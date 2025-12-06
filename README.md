# AI-Driven-Compliance-Guardian

This project aims to address the business issue by creating a runtime middleware system that acts as a compliance firewall between users and LLMs.

## Project Architecture

```text
+-----------------------+
|    Streamlit UI       |
|  (User Chat Frontend) |
+-----------+-----------+
            |
            v
+-----------------------+
|   FastAPI Middleware  |
|   Compliance Gateway  |
+-----------+-----------+
            |
            v
+-----------------------+     +----------------------+
|  Compliance Pipeline  | --> |   YAML Policy Engine |
|  Regex + NER + ML     |     |  (block/mask/allow)  |
+-----------+-----------+     +----------------------+
            |
            v
+-----------------------+
|   LLM (OpenAI/Groq)   |
+-----------------------+
```

## Setup Environment

## Setup Environment for Mac
### 1. Create environment
    python -m venv compliance_guardian_env

### 2. Activate environment
    source compliance_guardian_env/bin/activate

### 3. Install Database
    brew install sqlcipher

### 4. Install requirements.txt
    pip3 install -r requirements.txt

## Setup Environment for Windows
### 1. Create environment
    python -m venv compliance_guardian_env

### 2. Activate environment
    compliance_guardian_env\Scripts\activate

### 3. Install Database
    pip install sqlcipher3-wheels

### 4. Install requirements.txt
    pip install -r requirements.txt

## Run Application
### 1. Start API in Mac
#### Run command from root folder
    sudo uvicorn app.api.guardian_api:app --reload

### 1.1 Start API in Windows
#### Run command from root folder
    uvicorn app.api.guardian_api:app --reload

### 2. Start Streamlit Application
#### Open new terminal Run the command from root folder
    streamlit run app/streamlit/app.py

## Open application in browser
    http://localhost:8501/

## Use the following Credentials to login into Application

| Role | Username / Email | Password |
| :--- | :--- | :--- |
| **Admin** | `wehadi4324@bipochub.com` | `wehadi4324@bipochub.com` |
| **User** | `nokiv37278@feralrex.com` | `nokiv37278@feralrex.com` |


## Application Run analysis Mac Vs Windows

### Running on Mac mini (16 GB Memory)

### Performance was smooth, and the application responded quickly as expected.

### Running on Windows

### The application worked correctly but showed slightly slower response times compared to macOS.

