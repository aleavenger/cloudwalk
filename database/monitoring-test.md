# Monitoring analyst test

## Repository submission note

For this repository submission, start with:

- `../README.md` for reviewer bootstrap, services, and reproducibility
- `../report/presentation.md` for the primary reviewer-facing deliverable
- `../report/technical_report.md` for the detailed written explanation
- `../docs/monitoring-methodology.md` for the source-of-truth data-flow and methodology description

> “Where there is data smoke, there is business fire.” — 
Thomas Redman.<br/>

## 1. Introduction

This test is intended for candidates applying to Monitoring analyst positions at CloudWalk.
If you get here, we already like you and see you as a good fit with our company. 
Now, we propose a challenge similar to the ones that we face on a daily basis.

The challenges were created with the objective of helping you build the knowledge base needed to implement 
the technical assessment in the end, enjoy!

- The first challenge is an analysis of hypothetical data.
- The second challenge is the actual implementation of a solution to a real world problem. 

## 2. Pre-requisites

- A development environment

## 3. Tasks

### 3.1 - Get your hands dirty

Using [this csv](https://github.com/thais-menezes/monitoring/blob/main/checkout_1.csv)
and using [this csv](https://github.com/thais-menezes/monitoring/blob/main/checkout_2.csv)
 with hypothetical checkout data, imagine that you are trying to understand if there is any kind of anomaly behavior.

1. Analyze the data provided and present your conclusions .
2. In addition to the spreadsheet data, make a query in SQL and make a graphic of it and try to explain the anomaly behavior you found.
3. In this csv you have the number of sales of POS by hour comparing the same sales per hour from today, yesterday and the average of other days. So with this we can see the behavior from today and compare to other days

### 3.2 - Solve the problem

*Alert incident in transactions: Implement the concept of a simple monitoring with real time alert with notifications to teams.*

The monitoring works by receiving information about a transaction and inferring whether it is a failed or denied, or reversed or approved transaction. 
We work mostly with SQL, PromQL, Ruby and Python, but you can use any programming language that you want. 

Please use the data of [this csv](https://github.com/everton-cw/monitoring_test/blob/main/transactions.csv)
and the data of [this csv](https://github.com/everton-cw/monitoring_test/blob/main/transactions_auth_codes.csv). 
So with this data you can see the diferent status per minute and see if it is going well or not. When you see the padron, you can predict a alarm for the anomaly.

Your Monitoring alert system must have at least:
1 endpoint that receives transaction data and returns a recommendation to “alert” the anomalies found in transactions.
A query to organize the data on the data and a graphic to see the data in real time.
A model to determine anomalies and a system to report the anomalies automatically.

You are free to determine the methods for triggering the alerts, but a few ways to do it are:

- rule-based  - you define which cases get alerted based on predefined rules;
- score-base  - you create a method/model (you could use machine learning models here if you want)  to determine the anomaly
-- score of a transaction and make your decision based on it; 
- a combination of both;
 
#### Monitoring alert Requirements

- Alert transactions if failed transactions are above normal;
- Alert transactions if reversed transactions are above normal;
- Alert transactions if denied transactions are above normal;

## 4. Deliverables

* You must generate a document explaining how the challenge was executed (it can be a PDF, slides, or even text) that the team will use to complement the analysis of your execution, which must be included in a Github repository.

* Our team will review all the content of the presentation and the repository, and if it is within our expectations, we will schedule an interview where the team will ask some questions about the process and use of tools in the challenge, and will also explore your knowledge of other tools and processes in the area to understand your skills and potential.
