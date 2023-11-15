## Standard Library Imports ##
from collections import defaultdict
import logging
from pathlib import Path
import sys
from time import time

## Third-Party Imports (requires pip install) ##
from tqdm import tqdm
import pickle
import bz2, gzip


## Local Imports ##
# None


class StopExecution(Exception):
    # Redine "exit()" to be Jupyter safe
    # In Jupyter, calling "exit()" breaks the kernel, which is not what we want.
    # Instead, we want the notebook to stop running, which is a special execution break defined here.
    def _render_traceback_(self):
        pass


def exit():
    raise StopExecution


def defaultdict_to_dict(d):
    if isinstance(d, defaultdict):
        d = {k: defaultdict_to_dict(v) for k, v in d.items()}
    return d


class CustomLogger():
    """docstring for CustomLogger"""

    LOG_LEVEL_INTS = {
        'debug': 10,
        'info': 20,
        'warning': 30,
        'error': 40,
        'critical': 50,
    }

    class Block(object):
        """docstring for Block"""

        def __init__(self, name, log_level, timed):
            self.name = name
            self.log_level = log_level
            self.start_time = time() if timed else None

    def __init__(self, name, *, log_level=20, filename=None, space_chars='\t', verbose_newlines=False, suppress=False,
                 display_loglevel=True, display_datetime=True):

        # Instance variables
        self.space_chars = space_chars
        self.verbose_newlines = verbose_newlines
        self.suppress = suppress  # Currently not used. Integrate later
        self._blocks = []
        self._last_message = None

        # Initialise the real logger, which we will use in this custom logger
        format_str = ''
        if display_loglevel:
            format_str += '%(levelname)s '
        format_str += '%(message)s'
        arguments = {
            'stream': sys.stdout,  # This is for Jupyter to have the text NOT be red
            'format': format_str,
            'level': self._log_level_to_int(log_level),
        }
        # Also log to a file if the user has specified so
        if filename:
            arguments['filename'] = filename
            arguments['encoding'] = 'utf-8'
        if display_datetime:
            arguments['format'] = '%(asctime)s ' + arguments['format']
            arguments['datefmt'] = '%Y.%m.%d %H:%M:%S'
        # Initialise logger
        logging.basicConfig(**arguments)
        self.logger = logging.getLogger(name)

    def get_indent(self):
        return f"{self.space_chars * len(self._blocks)}"

    def _log_level_to_int(self, log_level):
        # Return log level if it already is a correct integer
        if log_level in self.LOG_LEVEL_INTS.values():
            return log_level
        # If a value log level string has been passed, we can conver to a number
        if log_level in self.LOG_LEVEL_INTS:
            return self.LOG_LEVEL_INTS[log_level]
        # At this point, the user (developer) has passed a value we cannot parse
        self.logger.warning('Warning to Developer: You have selected a log level that doesn\'t exist.')
        return None

    def log(self, log_level, message):
        self._log(log_level, message)

    def debug(self, message):
        self._log(10, message)

    def info(self, message):
        self._log(20, message)

    def warning(self, message):
        self._log(30, message)

    def error(self, message):
        self._log(40, message)

    def critical(self, message):
        # Log the message
        self._log(50, '')
        self._log(50, '!!!!!!!!!!!!!!!!!!!!!!!')
        self._log(50, '!!! CRITICAL ERROR !!!!')
        self._log(50, '!!!!!!!!!!!!!!!!!!!!!!!')
        self._log(50, f"\n{message}")
        # Clean up the blocks
        for _ in range(len(self._blocks)):
            self.end()
        # Kill the program
        # NOTE: When running Jupyter, this may kill the kernel, which wipes data and is generally bad
        # To avoid this, use a custom definition of exit that should be included in this file
        exit()

    def _log(self, log_level, message):

        # Only allow one blank space at a time. This makes for cleaner logs.
        if message == '' and self._last_message == '':
            return None
        # Add indentation based on nested block level
        message = f'{self.space_chars * len(self._blocks)}{message}'
        # Run the appropriate log level 
        self.logger.log(log_level, message)

    def start(self, name, *, log_level=20, timed=True):

        # Convert to int, in case the user passed a string
        log_level = self._log_level_to_int(log_level)

        # Custom log message when starting a block
        if self.verbose_newlines:
            self.log(log_level, '')
        self.log(log_level, f'[Start] {name}')
        if self.verbose_newlines:
            self.log(log_level, '')

        # Save this block so we can keep track of it
        self._blocks.append(self.Block(name, log_level, timed))

    def end(self):

        # Remove from blocks, and recover to utilise
        ended_block = self._blocks.pop()

        # If a timer was set, we want to add this to the output
        duration_str = ''
        if ended_block.start_time:
            duration_seconds = time() - ended_block.start_time
            M, S = divmod(duration_seconds, 60)
            H, M = divmod(int(M), 60)
            duration_str = f"Duration: {H:02d}:{M:02d}:{S:07.4f}"

        # Custom log message when ending a block
        if self.verbose_newlines:
            self.log(ended_block.log_level, '')
        self.log(ended_block.log_level, f'[ End ] {duration_str}')
        if self.verbose_newlines:
            self.log(ended_block.log_level, '')

    def reset(self):
        self._blocks = []


class PickleLib:

    def __init__(self, *, data_path='./', logger=None):
        self.data_path = data_path
        self.logger = logger

    @staticmethod
    def dict_to_filename_str(input_dict):
        def replace_chars(input_str):
            return (
                input_str
                .replace('-', '.')  # We want to reserve '-' for symbol separaters
                .replace(' ', '_')  # We want to keep the data maintainable, and spaces can be tricky
            )

        # Format the dict into str
        return '-'.join([f"{replace_chars(str(k))}-{replace_chars(str(v))}" for k, v in input_dict.items()])

    class TQDMBytesReader(object):

        def __init__(self, fd, desc, **kwargs):
            self.fd = fd
            self.tqdm = tqdm(**kwargs)
            self.tqdm.set_description_str(desc)

        def read(self, size=-1):
            bytes = self.fd.read(size)
            self.tqdm.update(len(bytes))
            return bytes

        def readline(self):
            bytes = self.fd.readline()
            self.tqdm.update(len(bytes))
            return bytes

        def __enter__(self):
            self.tqdm.__enter__()
            return self

        def __exit__(self, *args, **kwargs):
            return self.tqdm.__exit__(*args, **kwargs)

    def _configure_open_and_full_file_path(self, compression, filepath):
        # Switch the open function depending on the compression chosen
        if compression == None:
            open_func = open
        elif compression == 'gzip':
            open_func = gzip.open
        elif compression == 'bz2':
            open_func = bz2.BZ2File
        else:
            if self.logger:
                self.logger.error(
                    f"🥒 Chosen compression algorithm is not implemented: {compression}. "
                    f"Defaulting to standard 'open' function.")
            open_func = open

        # File extension appends the name of the compression algorithm
        file_ext = compression if compression else ''
        full_file_path = f"{filepath}.p{file_ext}"

        return open_func, full_file_path

    def pickle_dump(self, data, filepath, compression=None, silent=False):
        """Pickles an object.
        Parameters
            data : Any - Arbitrary Python object to be pickled
            filepath : str - Path to the file name to store the pickle
            compression : {None, gzip, bz2} - Chosen compression algorithm
                gzip: ~20% more time, ~10% pickle size (recommended)
                bz2: ~500% more time, ~5% pickle size
        Returns
            None
        """

        # NOTE: Larger Pickles..? https://stackoverflow.com/questions/31468117/python-3-can-pickle-handle-byte
        # -objects-larger-than-4gb

        # Configure variables based on compression algorithm chosen
        open_func, full_file_path = self._configure_open_and_full_file_path(compression, filepath)
        # Pickle the object
        if self.logger and not silent:
            self.logger.start(f"🥒 Dumping Data to Pickle: \"{full_file_path}\"")
        with open_func(full_file_path, 'wb') as file:
            # NOTE: It is unknown how to track progress of dumping a pickle
            # The size of the Python data is hard to calculate, and the size of the Pickle will be different
            pickle.dump(data, file)
        if self.logger and not silent:
            self.logger.end()

    def pickle_load(self, filepath, compression=None, silent=False):
        """Unpickles an object.
        Parameters
            filepath : str - Path to the file name where the pickle is stored
            compression : {None, gzip, bz2} - Chosen compression algorithm
        Returns
            Unpickled data
        """

        # Configure variables based on compression algorithm chosen
        open_func, full_file_path = self._configure_open_and_full_file_path(compression, filepath)

        # Unpickle the object
        if self.logger and not silent:
            self.logger.start(f"🥒 Loading data from Pickle: \"{full_file_path}\"")
        with open_func(full_file_path, 'rb') as file:
            # Get the filesize
            file.seek(0, 2)  # Go to the end of the file offset by 2 to read the filesize
            total_bytes = file.tell()  # Get the filesize
            file.seek(0)  # Go back to the beginning of the file
            # Get formatting information
            progress_bar_indent = ''
            if self.logger and isinstance(self.logger, CustomLogger):
                progress_bar_indent = self.logger.get_indent()
            # Unpickle the data with a progress bar based on the total bytes to be read
            with self.TQDMBytesReader(
                    file, f"{progress_bar_indent} Data", total=total_bytes, unit='B', unit_scale=True,
                    unit_divisor=1000,
                    ncols=100, ascii=True, disable=silent) as pbfd:
                data = pickle.load(pbfd)
        if self.logger and not silent:
            self.logger.end()
        return data

    def get_pickle_else_compute(self, compute_func, compute_args=None, *,
                                filename=None, fn_ignore_args=None, compression='gzip',
                                force_compute=False, pickle_dump=True):
        """Attempts to get pickled data, else it computes the data, saves it as a pickle, and then returns it.
        Parameters
            compute_func : function - The function to run to gather the data if the pickle cannot be found
            compute_args : dict - The arguments to pass to the compute_func function
            filename : str - File name where the pickle is stored, or will be stored after computing
            compression : {None, gzip, bz2} - Chosen compression algorithm.
            force_compute : Bool - Force the compute function to run, regardless of existing pickles (overwrite pickle)
            do_not_pickle : Bool - Do not create a pickle (mostly for testing)
        """

        if self.logger:
            self.logger.start(f"🥒 get_pickle_else_compute: {compute_func.__name__}")

        ## Adjust None args into Usable Variables ##
        if not compute_args:
            compute_args = {}
        if not filename:
            if not fn_ignore_args:
                fn_ignore_args = []
            # Create a filename that will be unique based on the compute function and arguments
            filename = (
                f"{compute_func.__name__}("
                f"{', '.join([f'{k}={v}' for k, v in compute_args.items() if k not in fn_ignore_args])}"
                f")"
            )
        filepath = f"{self.data_path}{filename}"

        # Configure variables based on compression algorithm chosen
        _, full_file_path = self._configure_open_and_full_file_path(compression, filepath)
        file_exists = Path(full_file_path).is_file()

        ## Execute Control Flow ##
        if force_compute or not file_exists:
            # Print appropriate reason why
            if force_compute:
                self.logger.info(f"🥒 Force Compute: {full_file_path}")
            elif not file_exists:
                self.logger.info(f"🥒 Pickle Not Found: {full_file_path}")
            # Compute the data
            data = compute_func(**compute_args)
            # Dump the pickle?
            if pickle_dump:
                self.pickle_dump(data, filepath, compression)
            else:
                self.logger.info('🥒 PickleDump False')
        else:
            data = self.pickle_load(filepath, compression)

        if self.logger:
            self.logger.end()

        return data


def defaultdict_to_dict(d):
    if isinstance(d, defaultdict):
        d = {k: defaultdict_to_dict(v) for k, v in d.items()}
    return d
