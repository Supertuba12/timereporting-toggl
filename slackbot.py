#!/usr/bin/python3
# -*- coding: utf-8 -*-
import time
from slackclient import SlackClient
import json
import requests
import create_report

with open('config.json') as data_file:
    config = json.load(data_file)

with open('members.json') as data_file:
    members = json.load(data_file)

# constants
AT_BOT = "<@" + config["slack_botID"] + ">"
EXAMPLE_COMMAND = "do"
BOT_NAME = 'kmm_timereportbot'

#USER_IDs = {"jennifer":"ffe092e4227c3d7a007c3f7e0bf09989", "rolf":"ec72c715d5ae3de5ae8320da06afded7", \
#            "hampus":"121b0860329ce70d2bfdc25f4d3e1a15", "erik":"ac59108bc502ddbb3c2840688a33e046", \
#            "sabina":"32b3588806bc735303a3db4f28709bb2", "william":"17f1b873d3749f8091115164243e3f76" \
#            }


slack_client = SlackClient(config["slack_key"])


class SlackBot:
    def __init__(self):
        self.report_text = ""
        self.sessions_ids = {}

    def handle_command(self, command, channel, user):
        """
            Receives commands directed at the bot and determines if they
            are valid commands. If so, then acts on the commands. If not,
            returns back what it needs for clarification.
        """
        print(members[user])
        if command.startswith("!report"):
            if "last" in command:
                file_name = create_report.generate_report(self.report_text, lastweek=True)
            else:
                file_name = create_report.generate_report(self.report_text)
            slack_client.api_call("files.upload", filename=file_name, channels=channel, file=open("full.pdf", "rb"))
        elif command.startswith("!start"):
            cmd_list = command.split(',', 1) # Split command and description into a list.
            if(len(cmd_list) == 2):
                description = cmd_list[-1] # Granted that description was given, declare it as a var.
                self.session_ids[user] = requests.post('https://www.toggl.com/api/v8/time_entries/start',
                                               json={"time_entry": {"description": description, "wid": members[user]['wid'], "created_with":"curl"}}, 
                                               auth=(members[user]['api_token'], "api_token")).json['data']['id']
                # Store the time entry ID given from POST request to toggl with user ID as key.
        elif command.startswith("!stop"):
            requests.put('https://www.toggl.com/api/v8/time_entries/' + 
                        self.sessions_ids[user] + '/stop', auth=(members[user]['api_token']))
            # Stop user's latest time entry.
            del self.sessions_ids[user] # Delete session ID from key "user".
        else:
            response = "Use \"!report\" to get latest report. " \
                        "Upload a text snippet named \"report\" to generate new report. \n" \
                        "Use \"!start\", [DESCRIPTION] to start your toggl timer " \
                        "and don't forget to stop with \"!stop\"."
            slack_client.api_call("chat.postMessage", channel=channel, text=response, as_user=True)

    def parse_slack_output(self,slack_rtm_output):
        """
            The Slack Real Time Messaging API is an events firehose.
            this parsing function returns None unless a message is
            directed at the Bot, based on its ID.
        """
        output_list = slack_rtm_output
        if output_list and len(output_list) > 0:
            for output in output_list:
                # print(output)
                if output and 'text' in output and AT_BOT in output['text']:
                    # return text after the @ mention, whitespace removed
                    return output['text'].split(AT_BOT)[1].strip().lower(), \
                           output['channel'], output['user']
                # Message was a file and that file was intended for bot (report.txt).
                if output and "file" in output and "name" in output["file"] and output["file"]["name"] == "report.txt":
                    # Save file. Use file to generate report and send file
                    report = requests.get(output["file"]["url_private_download"], headers={'Authorization': "Bearer " + config["slack_key"]})
                    report.encoding = "uft-8"
                    self.report_text = report.text
                    file_name = create_report.generate_report(self.report_text)
                    slack_client.api_call("files.upload", filename=file_name, channels=output['channel'], file=open("full.pdf", "rb"))
        return None, None, None
            

    def store_session_id(self, data, user):
        """
            Store a user's session id to make it possible to close said session
            on !stop command.
        """
                

    def main(self):
        READ_WEBSOCKET_DELAY = 1  # 1 second delay between reading from firehose
        if slack_client.rtm_connect():
            print("KMM bot connected and running!")
            while True:
                command, channel, user = self.parse_slack_output(slack_client.rtm_read())
                if command and channel and user:
                    self.handle_command(command, channel, user)
                time.sleep(READ_WEBSOCKET_DELAY)
        else:
            print("Connection failed. Invalid Slack token or bot ID?")

slack_bot = SlackBot()
slack_bot.main()
