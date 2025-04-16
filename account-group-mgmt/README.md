# Account Group setup and syncronization

## Prepare service principal having admin privilige
```
export DATABRICKS_HOST="https://accounts.cloud.databricks.com"
export DATABRICKS_ACCOUNT_ID="0d26daa6-5e44-4c97-a497-ef015f91254a"
export DATABRICKS_CLIENT_ID="client id"
export DATABRICKS_CLIENT_SECRET="client secret"
```

## Organization changes over time

1. org_chart.ver1.yaml

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

- Sync results of initial organizational structure: org_chart.ver1.yaml
```
➜  scratch git:(main) ✗ python user_group_sync.py org_chart.ver1.yaml
2025-04-16 11:44:14,143 - INFO - Existing group found: ENGINEERING
2025-04-16 11:44:14,143 - INFO - Existing group found: FRONTEND
2025-04-16 11:44:14,144 - INFO - Existing group found: BACKEND
2025-04-16 11:44:14,144 - INFO - Existing group found: DEVOPS
2025-04-16 11:44:14,144 - INFO - Existing group found: SALES
2025-04-16 11:44:14,144 - INFO - Existing group found: REGIONAL_SALES
2025-04-16 11:44:14,144 - INFO - Existing group found: HR
2025-04-16 11:44:14,144 - INFO - Existing group found: TRAINING
2025-04-16 11:44:14,144 - INFO - Existing group found: RECRUITMENT
2025-04-16 11:44:14,144 - INFO - Existing group found: EXECUTIVE
2025-04-16 11:44:14,144 - INFO - Existing group found: FUTURE_PROJECTS
2025-04-16 11:44:14,144 - INFO - Existing group found: PAST_PROJECTS
2025-04-16 11:44:14,144 - INFO - Existing group found: SOME_TF
2025-04-16 11:44:21,551 - INFO - Existing user found: Alice Kim (alice.kim@acme.com)
2025-04-16 11:44:27,376 - INFO - Existing user found: Bob Lee (bob.lee@acme.com)
2025-04-16 11:44:36,143 - INFO - Existing user found: David Choi (david.choi@acme.com)
2025-04-16 11:44:48,405 - INFO - Existing user found: Charlie Park (charlie.park@acme.com)
2025-04-16 11:45:00,394 - INFO - Existing user found: Eva Jung (eva.jung@acme.com)
2025-04-16 11:45:07,158 - INFO - Existing user found: Frank Moon (frank.moon@acme.com)
2025-04-16 11:45:08,059 - INFO - Existing user found: Grace Yoon (grace.yoon@acme.com)
2025-04-16 11:45:21,609 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-16 11:45:27,652 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-16 11:45:28,958 - INFO - Synchronization completed successfully
```

- Sync results of modified organizational structure: org_chart.ver2.yaml
```
➜  scratch git:(main) ✗ python user_group_sync.py org_chart.ver2.yaml 
2025-04-16 11:50:34,243 - INFO - Existing group found: ENGINEERING
2025-04-16 11:50:34,244 - INFO - Existing group found: FRONTEND
2025-04-16 11:50:34,244 - INFO - Existing group found: BACKEND
2025-04-16 11:50:34,244 - INFO - Existing group found: DEVOPS
2025-04-16 11:50:34,784 - INFO - Members added to group: 1 members -> Group ID 216797855855967
2025-04-16 11:50:34,785 - INFO - Updated parent relationship: DEVOPS -> 216797855855967
2025-04-16 11:50:34,785 - INFO - Existing group found: SALES
2025-04-16 11:50:34,785 - INFO - Existing group found: REGIONAL_SALES
2025-04-16 11:50:34,785 - INFO - Existing group found: HR
2025-04-16 11:50:34,785 - INFO - Existing group found: TRAINING
2025-04-16 11:50:34,785 - INFO - Existing group found: RECRUITMENT
2025-04-16 11:50:34,785 - INFO - Existing group found: EXECUTIVE
2025-04-16 11:50:34,785 - INFO - Existing group found: FUTURE_PROJECTS
2025-04-16 11:50:39,971 - INFO - Removed group 1009053924994174 from parent 357782097970744
2025-04-16 11:50:40,410 - INFO - Members added to group: 1 members -> Group ID 216797855855967
2025-04-16 11:50:40,410 - INFO - Updated parent relationship: DEVOPS -> 216797855855967
2025-04-16 11:50:47,582 - INFO - Existing user found: Alice Kim (alice.kim@acme.com)
2025-04-16 11:50:53,178 - INFO - Existing user found: Bob Lee (bob.lee@acme.com)
2025-04-16 11:51:01,848 - INFO - Existing user found: David Choi (david.choi@acme.com)
2025-04-16 11:51:14,464 - INFO - Existing user found: Charlie Park (charlie.park@acme.com)
2025-04-16 11:51:26,368 - INFO - Existing user found: Eva Jung (eva.jung@acme.com)
2025-04-16 11:51:33,238 - INFO - Existing user found: Frank Moon (frank.moon@acme.com)
2025-04-16 11:51:34,158 - INFO - Existing user found: Grace Yoon (grace.yoon@acme.com)
2025-04-16 11:51:47,680 - INFO - Existing user found: Helen Kwon (helen.kwon@acme.com)
2025-04-16 11:51:53,602 - INFO - Existing user found: Ian Bae (ian.bae@acme.com)
2025-04-16 11:51:54,365 - INFO - Synchronization completed successfully
```


## TODO
- Reduce sync time by optimize repetivie loading of users and groups information from account console
