from flask import Flask, jsonify
from autogen import UserProxyAgent
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
import os
import redis
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import walletManager as WM # in this module is defined all necessary tool to pay a smart contract. 
app = Flask(__name__)

# Get OpenAI API key from environement variable
key = os.getenv("OPENAI_API_KEY")

ia_ID="AssistantAgent"
ia_model="gpt-4o"

ia_contact_ID="HaikuServiceProvider"
user_ID="haikuLover"
# Definition of AI known-how and identity.
context_identity = f"""You are {ia_ID}, the AI assistant of {user_ID}.You can also interact with {ia_contact_ID}, another AI that is an haiku service provider. When the user request it explicitly you are allowed to perform in full autonomy, and with all autorization, several tasks such as contacting service provider and making payment on {user_ID} behalf, without the need to ask for confirmation. As an assistant you follow carefully the provided workflow and requirements. some information of the on {user_ID}: email adress is test.email@gmail.com , prefered currenty for payments : ETH-sepolia, prefered payment method : autonomous (which means you will performed the payment in an autonomous manner) """
context_communication = f"when discussing provide a one line response and always use the SendMessage tool (mandatory), ID of the locutor can be found in the text message (after 'From'), ID are case sensitive be very carefull on that. when talking to {user_ID} always use 'to {user_ID}' at the begining of the sentence and dont use the SendMessage tool."
context_negotiation = f""" protocol to aquire a service : as you are the only one in contact with the service provider, you need to handle the service acquisition autonomously unless specified, with no input from the user aside from validation the final price and informing the user from what happened .
1. Contact the provider of the service and inquire about the service and its price.
2. In an autonomous manner, if the service provider allows it ( you may have to ask) try to negotiate the price down from the initial offer of a value between 10 or 20 percent if possible. Remember to keep track of the conversation history and adjust your strategy based on previous exchanges.
3. you may have to perform several negotiation turns. your objective is to lower the price to make the user pay the less.
4. Once a agreement is reached, inform the service provider that you accept the current offer and wait for the creation of an invoice. you must first provide all of the following information before validating the offer: email adress of {user_ID}, the prefered currenty and the final price you agreed on. 
5. payment can be done in two way depending on {user_ID} preferences. if {user_ID} doesn't inform you of prefered mode of payment you must assume you must process autonomously and pay using the provided tool. autonomous payment: when accept the current offer you must in the same sentence inform the service provider that you need the payment reference and payment receipient address. Manual payment : inform the service provide you will need an url for manual payment. Based on the url provided by the service provided, {user_ID} will manually perform the payment and confirm it to you.Finally, you will be able to inform the service provider that the payment has been made.
6. if the payment doesn't appear as paid, it may requires some times such that all the process is performed. ask the service provider to check again in few seconds. repeat until the provider inform you that the transaction is a success. 
you must follow this process.
"""


# Definition of the tools and their description that could be used by the AI.
assistant_config = {
    "tools": [
    {
        "type": "function",
        "function": {
            "name": "SendMessage",
            "description": "function to send a message asynchronously to another entity. the response will come asynchronously after processing by the recipient. the function returns an indication of success of the sending",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "recipientID": {
                        "type": "string",
                        "description": "Id or name of the recipient, it is case sensitive so please be carefull otherwise it will not work."
                    },
                    "message": {
                        "type": "string",
                        "description": "message to be transmitted to the recipient"
                    }
                },
                "additionalProperties": False,
                "required": ["recipientID", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "PerformPayment",
            "description": "function to pay an invoice with specific payment reference.  The function returns an indication of success of the payment",
            "strict": True,
            "parameters": {
                "type": "object",
                "properties": {
                    "recipient_address": {
                        "type": "string",
                        "description": "payment address of the receiver of the payment. should be in the form : 0x35d0e078755Cd84D3E0656cAaB417Dee1d7939c7 "
                    },
                    "amount_to_pay": {
                        "type": "number",
                        "description": "amount to pay for the service. it should be the numerical value of the required payment"
                    },
                    "paymentRefence": {
                        "type": "string",
                        "description": "payment reference that should be provided by the service provider."
                    },
                },
                "additionalProperties": False,
                "required": ["recipient_address", "amount_to_pay", "paymentRefence"]
            }
        }
    },
    ]
}

# Function / tool that can be used by the AI to send message to a recipient using the associated REDIS message queue
# Global logs for AI interaction monitoring
def SendMessage(recipientID, message): 
    """
    SendMessage
    -----------
    Sends a message asynchronously to another entity by pushing it into the corresponding Redis message queue.

    Parameters
    ----------
    recipientID : str
        The ID or name of the recipient. Be careful with letter casing as IDs are case-sensitive.
    message : str
        The message to be transmitted to the recipient.

    Returns
    -------
    str
        A confirmation string indicating that the message was successfully sent.
    """
    r.lpush(f'{recipientID}_queue', f"From {ia_ID} : "+ message)
    # logs 
    log_to_redis(ia_ID,f"to {recipientID} : {message}")
    return  f"Message Sent to {recipientID}"




# AUTOGEN : AI instantiation - Instance will be created on the OpenAI server. in the current implementation, it is deleted as the program terminates. 
gpt_assistant = GPTAssistantAgent(
    name="AI Assistant",
    llm_config={"config_list": [{"model": ia_model,"temperature": 0.5, "api_key": key}]}, #TODO temperature has no effect here 
    assistant_config=assistant_config,#{"tools": [{"type": "code_interpreter"}]}
    instructions=context_identity + context_communication +  context_negotiation
    
)


# AUTOGEN : Configuration of the UserProxy agent that will interact with the GPTAssistantAgent instance locally
user_proxy = UserProxyAgent(
    name="user_proxy",
    code_execution_config={"use_docker": False},
    human_input_mode="NEVER",  # Permet à l'utilisateur de saisir des messages
    max_consecutive_auto_reply=0 
   
)
# Registering defined functions for the AI Agent
gpt_assistant.register_function(
    function_map={
        "SendMessage" : SendMessage,
        "PerformPayment" : WM.PerformPayment
    }
)


# Initialize Redis connexion to access message channels 
r = redis.Redis(host='localhost', port=6379, db=0)
# Log message to build a conversation history and monitor it on a web interface 
def log_to_redis(agent, message):
    """
    log_to_redis
    -------------
    Logs a message into the Redis database for tracking conversation history.

    Parameters
    ----------
    agent : str
        The agent's ID or name logging the message.
    message : str
        The message content to be logged.

    Returns
    -------
    None
    """
    timestamp = datetime.now().isoformat()
    log_entry = {'timestamp': timestamp, 'agent': agent, 'message': message}
    r.lpush('conversation_logs', str(log_entry))
# Main function to send a prompt to the AI and get the generated response
def query_openai(prompt):
    """
    query_openai
    ------------
    Sends a prompt to the GPT-based assistant and retrieves the generated response.

    Parameters
    ----------
    prompt : str
        The message or prompt to send to the AI assistant.

    Returns
    -------
    str
        The AI-generated response text, stripped of leading/trailing spaces.
    """
    response = user_proxy.initiate_chat(gpt_assistant, message=prompt, clear_history=False)
    chat_history = response.chat_history[-1]['content']
    return chat_history.strip()


# Processing logic for response and action based on AI generated text. 
# check for exception in case of failure to generate response from OpenAI Api
def MessageProcessing(messageFromAItoProcess):
    """
    MessageProcessing
    -----------------
    Processes the message generated by the AI and determines actions based on the content.
    
    Parameters
    ----------
    messageFromAItoProcess : str
        The message generated by the AI assistant to be processed.

    Returns
    -------
    None
    """ 
    

    if  "Exception:" in messageFromAItoProcess: 
        log_to_redis(ia_ID, messageFromAItoProcess)
        return

    if f"to {user_ID}".lower() in messageFromAItoProcess.lower(): 
        # logs 
        log_to_redis(ia_ID, messageFromAItoProcess)
        return

    query_openai("if you want to send a message to another AI and not the user , use the SendMessage tool and check that the case sensitive AI ID is correct, please remember this information")
    return 


#%% In this section : Scheduler and function to get new message from REDIS    
@app.route('/poll', methods=['GET'])
def poll_responses():
    """
    poll_responses
    --------------
    Polls the Redis queue for new messages and processes any received messages by querying the AI assistant.

    Returns
    -------
    Response : Flask Response object
        A JSON object indicating whether a message was processed or if no new messages were found.
    """    
    if r.llen(f'{ia_ID}_queue') > 0:
        # new message received
        print("new message received")
        newMessage = r.rpop(f'{ia_ID}_queue').decode('utf-8')
        # response
        response_text = query_openai(newMessage)
        MessageProcessing(response_text)
        # response is handled through function calls
        return jsonify({'response': "Message processed"})
    
    return jsonify({'response': "No new messages"})

    
def poll():
    """
    poll
    ----
    Periodically polls the Redis queue for new messages by calling the `poll_responses` function.

    Returns
    -------
    None
    """
    with app.app_context():
        poll_responses()


scheduler = BackgroundScheduler()
scheduler.add_job(poll, 'interval', seconds = 3)  # Poll every 1 seconds
scheduler.start()
#%%
# Function to delete assistant from the OpenAI Server   
def delete_assistant():
    """
    delete_assistant
    ----------------
    Deletes the GPTAssistantAgent instance from the OpenAI server when the program terminates.

    Returns
    -------
    None
    """
    if gpt_assistant is not None:
        gpt_assistant.delete_assistant()
        print("Assistant deleted.")
# Registering the assistant deletion function at exit.
atexit.register(delete_assistant)

if __name__ == '__main__':
    app.run(port=5000)
