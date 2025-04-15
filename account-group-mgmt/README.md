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

## NOTE
- initial loading time takes about 30 seconds if account has 128 groups, 3550 users.
