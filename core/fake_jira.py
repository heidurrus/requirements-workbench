"""An in-memory stand-in for the Atlassian MCP Jira tools, for tests and the e2e fake server.

It never talks to a network. Tool names and argument names match the real server.
"""
import datetime
import itertools


class FakeJira:
    def __init__(self, project_key="SBX", site="https://sandbox.atlassian.net", cloud_id="cloud-1",
                 localized=True):
        self.project_key, self.site, self.cloud_id = project_key, site, cloud_id
        self.issues = {}                       # key → {key, fields}
        self.calls = []                        # (tool, args) in order
        self.fail_on = {}                      # tool → exception to raise once
        self._n = itertools.count(1)
        names = ("Эпик", "История", "Задача", "Подзадача") if localized else ("Epic", "Story", "Task", "Sub-task")
        self.types = [{"id": "1", "name": names[0], "subtask": False, "hierarchyLevel": 1},
                      {"id": "2", "name": names[1], "subtask": False, "hierarchyLevel": 0},
                      {"id": "3", "name": names[2], "subtask": False, "hierarchyLevel": 0},
                      {"id": "4", "name": "Баг" if localized else "Bug", "subtask": False, "hierarchyLevel": 0},
                      {"id": "5", "name": names[3], "subtask": True, "hierarchyLevel": -1}]

    @staticmethod
    def _now():
        return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+0000"

    def call(self, tool, **args):
        self.calls.append((tool, args))
        if tool in self.fail_on:
            raise self.fail_on.pop(tool)
        return getattr(self, tool)(**args)

    @property
    def writes(self):
        return [c for c in self.calls if c[0] in ("createJiraIssue", "editJiraIssue", "createIssueLink")]

    # read tools
    def getAccessibleAtlassianResources(self):
        return [{"id": self.cloud_id, "url": self.site, "name": "sandbox", "scopes": ["read:page:confluence"]},
                {"id": self.cloud_id, "url": self.site, "name": "sandbox", "scopes": ["read:jira-work", "write:jira-work"]}]

    def getVisibleJiraProjects(self, cloudId, **_):
        return {"values": [{"key": self.project_key, "name": "Sandbox", "issueTypes": self.types}], "isLast": True}

    def searchJiraIssuesUsingJql(self, cloudId, jql, fields=None, maxResults=50, nextPageToken=None):
        found = []
        if jql.startswith("key in ("):
            keys = [k.strip() for k in jql[len("key in ("):-1].split(",")]
            found = [self.issues[k] for k in keys if k in self.issues]
        elif "labels in (" in jql:
            wanted = {x.strip().strip('"') for x in jql.split("labels in (", 1)[1].rstrip(")").split(",")}
            found = [i for i in self.issues.values() if wanted & set(i["fields"]["labels"])]
        return {"issues": found, "isLast": True}

    def getJiraIssue(self, cloudId, issueIdOrKey, fields=None, **_):
        return self.issues[issueIdOrKey]

    # write tools
    def createJiraIssue(self, cloudId, projectKey, issueTypeName, summary, description="", contentFormat=None,
                        parent=None, additional_fields=None, **_):
        assert projectKey == self.project_key, "pushed to the wrong project"
        assert issueTypeName in {t["name"] for t in self.types}, f"unknown issue type {issueTypeName}"
        if parent:
            assert parent in self.issues, f"unknown parent {parent}"
        key = f"{projectKey}-{next(self._n)}"
        self.issues[key] = {"key": key, "id": key, "fields": {
            "summary": summary, "description": description, "issuetype": {"name": issueTypeName},
            "parent": {"key": parent} if parent else None, "labels": list((additional_fields or {}).get("labels") or []),
            "updated": self._now()}}
        return {"id": key, "key": key, "self": f"{self.site}/rest/api/3/issue/{key}"}

    def editJiraIssue(self, cloudId, issueIdOrKey, fields, contentFormat=None, **_):
        issue = self.issues[issueIdOrKey]
        issue["fields"].update(fields)
        issue["fields"]["updated"] = self._now()
        return issue

    def touch_in_jira(self, key, **fields):
        """Simulate someone editing the issue in Jira."""
        self.issues[key]["fields"].update(fields)
        self.issues[key]["fields"]["updated"] = (datetime.datetime.now(datetime.timezone.utc)
                                                 + datetime.timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")
