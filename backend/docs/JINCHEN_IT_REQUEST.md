# Jinchen MES Integration Questionnaire

**To:** Renewsys IT / Jinchen DBA Team
**Subject:** Technical requirements for AI Chatbot integration with Jinchen MES

The AI Chatbot requires read-only access to historical production data to answer natural language queries. To proceed with the integration, please provide the following technical details regarding the Jinchen MES server at `10.69.12.20`.

---

## Part 1: Connectivity & Network

1. **What service is running at `10.69.12.20:8000`?**
   - [ ] Relational Database (e.g., SQL Server, MySQL, PostgreSQL, Oracle)
   - [ ] REST API / Web Service
   - [ ] Middleware / Message Broker
   - [ ] Other: ________________

2. **If it is a Database, what is the Engine and Version?**
   - Engine: ________________
   - Version: ________________

3. **Network Reachability:**
   - Are there any VPNs, firewalls, or IP whitelisting requirements for our application server to reach `10.69.12.20`?
   - Answer: ________________

---

## Part 2: Authentication & Security

1. **Read-Only Account:**
   - Can you provision a dedicated **read-only** account for the chatbot? (Write access is strictly forbidden by project requirements).
   - Username: ________________
   - Password: [Please provide via secure channel, not email]

2. **If it is an API:**
   - What is the authentication method? (e.g., Bearer Token, Basic Auth, API Key).
   - Base URL: ________________

---

## Part 3: Schema & Data Mapping

To calculate metrics, the chatbot requires raw production records aggregated by Shift, Line, and Area.

1. **Table / Endpoint Name:**
   - What is the name of the primary table (or view/endpoint) containing line/shift-level production data?
   - Table/Endpoint Name: ________________

2. **Column / Field Names:**
   Please provide the exact database column names (or JSON keys) for the following:
   - **Production Date/Time:** ________________
   - **Production Line (e.g., KM1):** ________________
   - **Shift (e.g., A/B/C):** ________________
   - **Module Entering Station (Get-In):** ________________
   - **Module Leaving Station (Departure):** ________________
   - **Defective / Bad Quantity:** ________________
   - **Scrap Quantity:** ________________

3. **Timezone:**
   - What timezone are the database timestamps stored in? (e.g., UTC, IST, China Standard Time).
   - Answer: ________________

---

## Part 4: Pending Business Definitions (Optional but recommended)

If known by the IT/DBA team, how are the following tracked in the Jinchen schema?
1. **WIP (Work in Progress):** ________________
2. **Process Loss:** ________________
3. **Reworked Modules:** ________________
4. **Machine Downtime Logs:** ________________

Thank you for your assistance.
