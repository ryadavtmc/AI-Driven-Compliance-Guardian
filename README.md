# AI-Driven-Compliance-Guardian
This project aims to address the business issue by creating a runtime middleware system that acts as a compliance firewall between users and LLMS. 

## Setup Environment
Create Python environment -  python3 -m venv compliance_guardian_env
Activate python environment - source/compliance_guardian_env/bin/activate

# Install all dependencies
Run requirements.txt - pip3 install -r requirements.txt

## Install database
If you are in mac 
brew install sqlcipher

## Run api
sudo uvicorn app.api.guardian_api:app --reload


#### Run streamlit
streamlit run app/streamlit/app.py

##### Note:
Adim user: wehadi4324@bipochub.com
Password: wehadi4324@bipochub.com

User: nokiv37278@feralrex.com
password: nokiv37278@feralrex.com


##### Run with docker

docker build -t compliance-guardian:latest .
docker run -p 8501:8501 -p 8000:8000 --env-file .env compliance-guardian:latest


# Build Docker image
docker build -t compliance-guardian:latest .
docker run -p 8501:8501 -p 8000:8000 --env-file .env compliance-guardian:latest

### If Docker locked
security unlock-keychain ~/Library/Keychains/login.keychain-db

