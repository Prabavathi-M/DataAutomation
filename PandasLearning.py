import pandas as pd
from pandas._testing import assert_frame_equal
from pandas.io.formats.csvs import CSVFormatter
from pandas.io.sas.sas_constants import column_data_length_length

#Sample Test case Data
data={ 'TestCaseID': ['TC001','TC002','TC003','TC004','TC005'],
       'Module':['Login','Login','signup','signup','profile'],
       'Status':['Pass','Fail','Pass','Fail','Fail']
       }
#Create a Dataframe
df=pd.DataFrame(data)

#Small Learnings
print("Head",df.head()) #view the first 5 rows
print("Shape",df.shape) #get rows,columns
print("Status",df['Status']) #access single column
print("Access first row by index",df.iloc[0]) #access first row by index label

#Filter only failed test data
failed=df[df['Status']=='Fail']
print("Failed:",failed)
#Count Failures per module
fail_summary =  failed.groupby('Module').size()#.reset_index(name='Failed_Count')

#Save Summary to CSV
fail_summary.to_csv('Failed_Summary.csv',index=False)

#print results
print ('Failed test cases summary:')
print (fail_summary)

expected={
       'Name':'Chhavi'
}
Actual={
       'Name':'Chhaavi'
}
e_df=pd.DataFrame(expected,index=[0])
a_df=pd.DataFrame(Actual,index=[0])
assert_frame_equal(e_df,a_df)
