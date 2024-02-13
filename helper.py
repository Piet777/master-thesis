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
        comments['Created'] = row['history_created_date']
        comments['Comment'] = row['data_to']
        comments_df = pd.DataFrame(comments, index=[ind])
        output = pd.concat([output, comments_df])
        ind += 1

    return output


def saveTicket(prompt, df, evolutionStep, jira, id):
    try: 
        df.to_csv("data/" + str(prompt) + "/csv/" + str(jira) + "_" + str(id) + "_" + str(evolutionStep) + ".csv", index=False)
        df.to_json("data/" + str(prompt) + "/json/" + str(jira) + "_" + str(id) + "_" + str(evolutionStep) + ".json", orient='records', lines=True, indent=4)
        print("The files were saved successfully!")
    except:
        print("An error occurred while saving the files!")


def addIssueTypeToField(df, field):
    # reduces the dataframe to only the field you are looking for with the addition of a new column with the issue type
    # needs the full dataframe and the field as string
    
    df_reduced = df.loc[(df["field"] == field) | (df["field"] == "IssueType")]

    issue_type_df = df_reduced[df_reduced["field"] == "IssueType"]

    issue_type_dict = dict(zip(issue_type_df['issue_id'], issue_type_df['data_to']))

    df_reduced['issue_type'] = df_reduced['issue_id'].map(issue_type_dict)

    output = df_reduced[df_reduced["field"] == field]

    return output