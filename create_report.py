import requests
import datetime
from pylatex import Document, Section, Subsection, Tabular, Command, base_classes, NoEscape, LongTable
from pylatex.utils import bold
import json

with open('config.json') as data_file0:    
    config = json.load(data_file0)

with open('members.json') as data_file1:
    members = json.load(data_file1)

geometry_options = {"tmargin": "1cm", "lmargin": "1cm"}

def extract_time(json):
    try:
        return (json['user'], json["start"])
    except KeyError:
        return 0


def iso_time_to_datetime(time_str):
    k = time_str.rfind(":")
    time_str = time_str[:k] + time_str[k+1:]
    return datetime.datetime.strptime(time_str, '%Y-%m-%dT%H:%M:%S%z')


def generate_report(extra_text="", lastweek=False):
    doc = Document(geometry_options=geometry_options, documentclass =  Command('documentclass', options=base_classes.Options('a4paper'), arguments='article'))
    
    if lastweek:
        monday = datetime.date.today() + datetime.timedelta(days=-(datetime.date.today().weekday()+7))
    else:
        monday = datetime.date.today() + datetime.timedelta(days=-datetime.date.today().weekday())
    if lastweek:
        until = datetime.date.today() + datetime.timedelta(days=-(datetime.date.today().weekday()+1))
    else:
        until = datetime.date.today()
    
    # Get the group's report. Use arbitrary user_ID as key to members.
    detailed_report = requests.get('https://toggl.com/reports/api/v2/details', 
                                    params={'user_agent': config["user_agent"], 'workspace_id': config["workspace_id"][0], "since": str(monday), "until": str(until)}, 
                                    auth=(members['XXXXXXXXX']['api_token'], "api_token")).json()['data']
    # Add extra person's report to the final report. Use this person's user_ID.
    detailed_report += requests.get('https://toggl.com/reports/api/v2/details', 
                                    params={'user_agent': config["user_agent"], 'workspace_id': config["workspace_id"][1], "since": str(monday), "until": str(until)}, 
                                    auth=(members['XXXXXXXXX']['api_token'], "api_token")).json()['data']
    detailed_report.sort(key=extract_time, reverse=False)  # Sort first by user and then by start time
    with doc.create(Section('Status')):
        doc.append(extra_text.replace("\r\n","\n"))

    with doc.create(Subsection('Tidsrapport vecka ' + until.strftime("%V"))):
        with doc.create(LongTable('|l|p{5cm}|l|l|l|')) as table:
            rowcolor = "white"
            lastuser = ""
            table.add_hline()
            table.add_row(["Person", "Aktivitet", "Start", "Slut", "Timmar"], mapper=[bold])


            for event in detailed_report:
                # Toggle color between users
                if lastuser != event["user"]:
                    lastuser = event["user"]
                    if rowcolor == "white":
                        rowcolor = "lightgray"
                        # rowcolor = "#34DDDD"
                    else:
                        rowcolor = "white"

                start_time = iso_time_to_datetime(event["start"])
                end_time = iso_time_to_datetime(event["end"])

                table.add_row([event["user"], event["description"], 
                                start_time.strftime("%a %Y-%m-%d kl. %H:%M"), 
                                end_time.strftime("%a %Y-%m-%d kl. %H:%M"), end_time-start_time], 
                                color=rowcolor)
                table.add_hline()
    # Gather summary for the group's report 
    summary_report = requests.get('https://toggl.com/reports/api/v2/summary', 
                                    params={'user_agent': config["user_agent"], 'workspace_id': config["workspace_id"][0], "since": str("2017-01-16"), "grouping":"users", "subgrouping": "projects"}, 
                                    auth=(members['XXXXXXXXX']['api_token'], "api_token")).json()["data"]
    # Add extra person to summary.
    summary_report += requests.get('https://toggl.com/reports/api/v2/summary', 
                                    params={'user_agent': config["user_agent"], 'workspace_id': config["workspace_id"][1], "since": str("2017-01-16"), "grouping":"users", "subgrouping": "projects"}, 
                                    auth=(members['XXXXXXXXX']['api_token'], "api_token")).json()["data"]
    with doc.create(Section('Hela projektet')):
        for user in summary_report:
            doc.append("%s har %.2f timmar kvar. %.2f timmar avklarade. \n" % (user["title"]["user"],  160-user["time"]/1000/60/60, user["time"]/1000/60/60))
    doc.generate_pdf('full', clean=False, clean_tex=False)

    return str(monday)+"to"+str(until)+".pdf"

if __name__ == '__main__':
    generate_report()
