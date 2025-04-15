# Account Group setup and syncronization

## Prepare service principal having admin privilige
```
export DATABRICKS_HOST="https://accounts.cloud.databricks.com"
export DATABRICKS_ACCOUNT_ID="0d26daa6-5e44-4c97-a497-ef015f91254a"
export DATABRICKS_CLIENT_ID="client id"
export DATABRICKS_CLIENT_SECRET="client secret"
```

## Organization changes over time

1. org_chart.yaml

```
graph TD
    ORG[조직도]

    ORG --> ENGINEERING[ENGINEERING]
    ENGINEERING --> FRONTEND[FRONTEND]
    ENGINEERING --> BACKEND[BACKEND]
    ENGINEERING --> DEVOPS[DEVOPS]
    FRONTEND --> AliceKim[Alice Kim]
    FRONTEND --> BobLee[Bob Lee]
    BACKEND --> DavidChoi[David Choi]
    DEVOPS --> CharliePark[Charlie Park]

    ORG --> SALES[SALES]
    SALES --> REGIONAL_SALES[REGIONAL_SALES]
    REGIONAL_SALES --> EvaJung[Eva Jung]

    ORG --> HR[HR]
    HR --> TRAINING[TRAINING]
    HR --> RECRUITMENT[RECRUITMENT]
    TRAINING --> FrankMoon[Frank Moon]
    RECRUITMENT --> GraceYoon[Grace Yoon]

    ORG --> EXECUTIVE[EXECUTIVE]
    EXECUTIVE --> HelenKwon[Helen Kwon]
    EXECUTIVE --> IanBae[Ian Bae]

    ORG --> FUTURE_PROJECTS[FUTURE_PROJECTS]
```

2. org_chart.ver2.yaml

```
graph TD
    ORG[조직도]

    ORG --> ENGINEERING[ENGINEERING]
    ENGINEERING --> FRONTEND[FRONTEND]
    FRONTEND --> AliceKim[Alice Kim]
    FRONTEND --> BobLee[Bob Lee]

    ENGINEERING --> BACKEND[BACKEND]
    BACKEND --> DavidChoi[David Choi]
    BACKEND --> DEVOPS[DEVOPS]
    DEVOPS --> CharliePark[Charlie Park]

    ORG --> SALES[SALES]
    SALES --> REGIONAL_SALES[REGIONAL_SALES]
    REGIONAL_SALES --> EvaJung[Eva Jung]

    ORG --> HR[HR]
    HR --> TRAINING[TRAINING]
    HR --> RECRUITMENT[RECRUITMENT]
    TRAINING --> FrankMoon[Frank Moon]
    RECRUITMENT --> GraceYoon[Grace Yoon]

    ORG --> EXECUTIVE[EXECUTIVE]
    EXECUTIVE --> HelenKwon[Helen Kwon]
    EXECUTIVE --> IanBae[Ian Bae]

    ORG --> FUTURE_PROJECTS[FUTURE_PROJECTS]

```

## Syncronization logs

```
➜  scratch git:(main) ✗ python user_group_sync.py org_chart.yaml 
2025-04-15 18:32:38,167 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-15 18:32:38,683 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:32:45,335 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-15 18:32:45,752 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:32:45,984 - INFO - Synchronization completed successfully
➜  scratch git:(main) ✗ python user_group_sync.py org_chart.ver2.yaml
2025-04-15 18:33:47,359 - INFO - Members added to group: 1 members -> Group ID 216797855855967
2025-04-15 18:33:47,359 - INFO - Updated parent relationship: DEVOPS -> 216797855855967
Group(display_name='DEVOPS', entitlements=[], external_id=None, groups=[], id='1009053924994174', members=[], meta=None, roles=[], schemas=None)
2025-04-15 18:33:50,438 - INFO - Removed group 1009053924994174 from parent 357782097970744
2025-04-15 18:33:50,844 - INFO - Members added to group: 1 members -> Group ID 216797855855967
2025-04-15 18:33:50,844 - INFO - Updated parent relationship: DEVOPS -> 216797855855967
2025-04-15 18:34:05,253 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-15 18:34:05,764 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:34:12,106 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-15 18:34:12,726 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:34:12,987 - INFO - Synchronization completed successfully
➜  scratch git:(main) ✗ python user_group_sync.py org_chart.yaml     
2025-04-15 18:34:57,212 - INFO - Members added to group: 1 members -> Group ID 357782097970744
2025-04-15 18:34:57,213 - INFO - Updated parent relationship: DEVOPS -> 357782097970744
Group(display_name='DEVOPS', entitlements=[], external_id=None, groups=[], id='1009053924994174', members=[], meta=None, roles=[], schemas=None)
2025-04-15 18:35:00,754 - INFO - Removed group 1009053924994174 from parent 216797855855967
2025-04-15 18:35:01,263 - INFO - Members added to group: 1 members -> Group ID 357782097970744
2025-04-15 18:35:01,263 - INFO - Updated parent relationship: DEVOPS -> 357782097970744
2025-04-15 18:35:15,772 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-15 18:35:16,232 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:35:22,138 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-15 18:35:22,578 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:35:22,814 - INFO - Synchronization completed successfully
➜  scratch git:(main) ✗ python user_group_sync.py org_chart.yaml
2025-04-15 18:36:24,012 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-15 18:36:24,514 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:36:30,530 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-15 18:36:30,985 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:36:31,232 - INFO - Synchronization completed successfully
```

## NOTE
- initial loading time takes about 30 seconds if account has 128 groups, 3550 users.


## TODO
- bug fix unnecessary user sync
2025-04-15 18:36:24,012 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-15 18:36:24,514 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:36:30,530 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-15 18:36:30,985 - INFO - Members added to group: 1 members -> Group ID 663409434560886
2025-04-15 18:36:31,232 - INFO - Synchronization completed successfully