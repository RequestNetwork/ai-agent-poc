# Proof of Concept: AI Agent using Request Network
Proof of Concept of AIs Interaction for Autonomous Service Negotiation, Invoice generation and Payment Using a simple Request Network API

![conversationSample](https://github.com/user-attachments/assets/78a3f30e-4561-45a2-a7db-03f4a4013817)

Requirement : <br />
pip install apscheduler <br />
Redis 5.0.7 (pip install redis)   :  DB server used for communication between AIs and user , require additionnal downloads to run the Redis server.  <br />
tenacity-9.0.0 (pip install tenacity) <br />
pyautogen-0.2.33 (pip install --upgrade pyautogen) <br />
openai-1.40.0 (pip install --upgrade openai) <br />
pip install openai_multi_tool_use_parallel_patch <br />

## NOTES:
Redis for windows is available through the microsoft archive on github : https://github.com/microsoftarchive/redis/releases , I have used the version 3.0.504

To run these scripts in the same condition, you will need several prerequisites:
in the following, all the required key could be saved in your system environement variables. All required key and values will be indicated in the scripts by the os.getenv function call.

1) Set up the env variable `RequestNetwork_API_KEY = ""` for the Request Network Auth
2) An OpenAI API Key and a positive credit balance (to make api calls)
2) An Ethereum wallet with two addresses one for the payment of invoice and the other to receive the funds. you will also need your metamask account private key.
3) An Infura URL for Sepolia network and your api key

Before starting the web_interface.py, start your Redis server.
then start the two agent flask web servers AssistantAgent and ServiceProviderAgent.

Using you web browser, go to the web_interface url  to access the interface.

It may happens that the communication protocol between AI may not be respected, restarting the script should be sufficient to solve the issue.

All the transaction are executed on the Sepolia testnet, a testing network for Ethereum.

Enjoy !

## Acknowledgements

This project was initially developed in a [private repository](https://github.com/EchoOfHaiku/AI-KU) by @Doctatur with contributions from @vrolland on behalf of the Request Network Foundation.