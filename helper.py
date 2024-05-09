## Imports ##
import pandas as pd


## Functions ##
def createTicket(ticket, evolutionStep = None):
    #This function creates a ticket with all its evolutions or only the one specified by the evolutionStep parameter
    if evolutionStep is not None:
        if evolutionStep < 0:
            print("The evolution step must be a positive number.")
            return None
        elif ticket['history_order'].max() < evolutionStep:
            print("The maximum for the evolution step is: " + str(ticket['history_order'].max()) + ". Please choose a lower one.")
            return None
    
    filteredTicket = ticket.filter(['jira', 'issue_id', 'history_order', 'history_author', 'history_created_date', 'field', 'data_to'], axis=1)
    
    headers = ['Jira', 'IssueId', 'EvoId', 'Summary', 'Description', 'VersionsAffected', 'IssueType',
       'Project', 'Components', 'CreatedDate', 'ResolvedDate', 'Status',
       'Priority', 'Creator', 'Reporter', 'Comments', 'Resolution',
       'IssueLinks', 'Labels', 'Environment', 'VersionsFixed', 'Assignee',
       'TimeEstimateOriginal', 'TimeEstimateRemaining', 'Rank', 'Parent',
       'Sprint', 'TimeSpent', 'Flagged']

    newTicket = pd.DataFrame(columns=headers)
       
    data_to_map = {}
    for index, row in filteredTicket.iterrows():
            data_to_map['Jira'] = row['jira']
            data_to_map['IssueId'] = row['issue_id']
            data_to_map['EvoId'] = row['history_order']
            data_to_map['HistoryAuthor'] = row['history_author']
            data_to_map['Updated'] = row['history_created_date']
            field = row['field']
            data_to_map[field] = row['data_to']

            sample_df = pd.DataFrame(data_to_map, index=[0])
            newTicket = pd.concat([newTicket, sample_df], axis=0)

    result = newTicket.groupby(['EvoId']).last().reset_index()

    if evolutionStep is not None:
        result = getEvoStep(result, filteredTicket, evolutionStep)
    
    return result


def getEvoStep(ticket, dfsample, step):
    # dfsample = dfsample.filter(['jira', 'issue_id', 'history_order', 'history_author', 'history_created_date', 'field', 'data_to'], axis=1)
    ticket = ticket.filter(['Jira', 'IssueId', 'EvoId','Summary','Description','VersionsAffected','IssueType','Project','Components','CreatedDate','ResolvedDate','Status','Priority','Creator','Reporter','Resolution','IssueLinks','Labels','VersionsFixed','Assignee','TimeSpent'], axis=1)
    
    row = ticket[ticket['EvoId'] == step]

    dfSampleByEvoId = dfsample[dfsample['history_order'] <= step]

    comment_history = createCommentsHistory(dfSampleByEvoId[dfSampleByEvoId['field'] == 'Comments'])
    row.loc[:, 'Comments'] = [comment_history]

    return row


def createCommentsHistory(data):
    #data is the content of the Comments field of a ticket
    comments = {}
    output = pd.DataFrame(columns=['Author', 'Created', 'Comment'])
    
    ind = 0
    for index, row in data.iterrows():
        comments['Author'] = row['history_author']
        comments['Created'] = row['history_created_date'].strftime('%Y-%m-%d %H:%M:%S')
        comments['Comment'] = row['data_to']
        comments_df = pd.DataFrame(comments, index=[ind])
        output = pd.concat([output, comments_df])
        ind += 1

    return output


def saveTicket(folderName, ticket, evolutionStep, jira, id):
    try: 
        ticket.to_json("data/" + str(folderName) + "/" + str(jira) + "_" + str(id) + "_" + str(evolutionStep) + ".json", orient='records', lines=True, indent=4)
        print("The JSON was successfully saved!")
        
        if folderName == "summary":
            createSummaryAnnotation(ticket)
            insertIntoDataset(folderName, ticket)
    
    except:
        print("An error occurred while saving the files!")


def insertIntoDataset(folderName, ticket):
    try:
        dataset = pd.read_csv("data/" + folderName + "/" + folderName + "Dataset.csv")

        if ((dataset['Jira'] == ticket['Jira'][0]) & (dataset['IssueId'] == ticket['IssueId'][0])).any():
            print("The ticket is already in the dataset.")
        else:
            ticket.to_csv("data/" + str(folderName) + "/" + str(folderName) + "Dataset.csv", mode='a', header=False, index=False)
            print("The ticket was inserted into the dataset successfully!")
    except:
        print("An error occurred while inserting the file!")


def createSummaryAnnotation(ticket):        
    summary = ticket['Summary'][0]
    summaryLength = len(str(summary))

    if(summaryLength > 70):
        ticket['SmellActual'] = "TRUE"
        ticket['SmellReason'] = str(summaryLength) + " characters is too long."
    elif(summaryLength < 39):
        ticket['SmellActual'] = "TRUE"
        ticket['SmellReason'] = str(summaryLength) + " characters is too short."
    else:
        ticket['SmellActual'] = "FALSE"
        ticket['SmellReason'] = str(summaryLength) + " characters is in range."
    
    print("The annotation was created successfully!")


def annotateResult(result, ticket, prompt_type):
    try:
        if prompt_type == "summary":
            createSummaryAnnotationForResult(result, ticket)
        elif prompt_type == "update":
            createUpdateAnnotationForResult(result, ticket)
        elif prompt_type == "bugreportStructure":
            createBugReportAnnotationForResult(result, ticket)
        else:
            print("no annotation method for the prompt type")
            
    except:
        print("An error occurred while annotating the result!")


def createSummaryAnnotationForResult(result, ticket):        
    summary = ticket['Summary']
    summaryLength = len(str(summary))

    if(summaryLength > 70):
        result['smell_actual'] = "TRUE"
        result['reason'] = str(summaryLength) + " characters is too long."
    elif(summaryLength < 39):
        result['smell_actual'] = "TRUE"
        result['reason'] = str(summaryLength) + " characters is too short."
    else:
        result['smell_actual'] = "FALSE"
        result['reason'] = str(summaryLength) + " characters is in range."
    
    print("The annotation was created successfully!")


def createBugReportAnnotationForResult(result, ticket):
    dataset = pd.read_csv("./data/bugreportStructure/bugreportStructureDataset.csv")
    jira = ticket['Jira']
    issueId = ticket['IssueId']
    evoId = ticket['EvoId']

    try:
        dataset_entry = dataset[(dataset['Jira'] == jira) & (dataset['IssueId'] == issueId) & (dataset['EvoId'] == evoId)]
        
        result['smell_actual'] = str(dataset_entry['SmellActual'].values[0])
        result['reason'] = str(dataset_entry['SmellReason'].values[0])
        print("The annotation was created successfully!")
    except:
        print("The ticket is not in the dataset.")
    

def createUpdateAnnotationForResult(result, ticket):
    dataset = pd.read_csv("./data/update/updateDataset.csv")
    jira = ticket['Jira']
    issueId = ticket['IssueId']
    evoId = ticket['EvoId']

    dataset_entry = dataset[(dataset['Jira'] == jira) & (dataset['IssueId'] == issueId) & (dataset['EvoId'] == evoId)]

    if dataset_entry['ViolationActual'].values[0]:
        violation = "TRUE"
    elif not dataset_entry['ViolationActual'].values[0]:
        violation = "FALSE"

    result['violation_actual'] = violation
    result['reason'] = dataset_entry['ViolationReason'].values[0]

    print("The annotation was created successfully!")