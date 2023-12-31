# osuAnonmap
Essentially the same tool as https://github.com/pishifat/contest-anonymization#readme but in Python without required installed packages (afaik everything comes with regular python 3.10 install)


Setup:

In the folder containing these python files, put a zip file formatted like the MPG contest download. This means a zip file containing a folder (named after creator) containing an osz file. 
Go into config.json - change tournament name and number of allowed diffs. 

If 
```
numberDiffs = 0
```
we operate under the asssumption that any number of difficulties is allowed. Any positive integer assumes exact match.

Create token.json with the following format:
```
{
  "token": "<your legacy osuAPI token>"
}
```

Your API key can be found under the settings on your profile page.

For Taiko contests, go into config.json and change 

```
"taiko":"False" 
```
to 
```
"taiko":"True"
```

To run:
Navigate to the folder you stored this code and run main.py with
```
python ./main.py
```

In the output folder you will find a zip file containing anonymized .osz files. The .csv file you will find in there will be in the exact same format as MPG requires to undo the anonymization.
For contest integrity, do NOT share the mask.csv. Do also NOT share token.json as that holds your personal osu API token.
