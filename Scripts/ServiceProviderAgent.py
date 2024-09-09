from flask import Flask, jsonify
from autogen import UserProxyAgent
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
import os
import redis
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import InvoiceManager as IM
app = Flask(__name__)
# Get OpenAI API key from environement variable
key = os.getenv("OPENAI_API_KEY")


ia_ID="HaikuServiceProvider"
ia_model="gpt-4o"

ia_contact_ID="AssistantAgent"
# Definition of AI known-how and identity.
context_identity =f"You are {ia_ID}. you are an service provider of haiku. you must insist on the fact that this service should be first paid before sending the haiku. "
context_communication = "when discussing provide a one line response and always use the SendMessage tool (mandatory), ID of the locutor can be found in the text message after the 'From' statement, ID are case sensitive, you will have to discuss and eventually enter a negotiation process to perform the trade. if a message is meant to be sent to another locutor, use the SendMessage function, else start your sentence with 'Internal Message: '.  please remember this information "
context_negotiation = """
The initial price for a haiku creation is 0.001 ETH-sepolia.
Your goal is to maintain the price as close as possible to the initial price, but you can accept a maximum of 5 percent discount. Mandatory: Do not tell the minimum price directly as your target is to earn the highest price but stay open for negotiation for instance you can say the proposed price is too low.
Respond to the offers and counteroffers to reach an agreement.
Once an agreement is reached, the payment must be made by first sending a custom invoice using the SendInvoice tool and the provided information :  email adress of the buyer, currency, you will provide the other parameters.
if this information are not provided, ask each of them until you have it all.
before generating the invoice, if it is not clear, ask the client if the payment reference should be provided or the url for manual payment. 
you will send the invoice information so the invoice can be payed.
once payment is supposed to be done, you must check and confirm the status of the invoice using CheckInvoiceStatus tool until the status is indicated as paid. this is your confirmation of payment. 
once the payment status is indicated as paid, you can respond with a beautiful haiku to end the trade. 
Remember the conversation history and adjust your strategy accordingly.
"""
# Definition of the tools and their description that could be used by the AI.
assistant_config = { 
    "tools": [{
        "type": "function",
        "function": {
            "name": "CheckInvoiceStatus",
            "strict": True,
            "description": "get the current status of an invoice according to its ID to be passed in input. the function returns a string explaining the current status. when an invoice is paid, the status will be indicated as such. for instant ouput may look like : 'current status of invoice ID 66c0f71820eb9ce52a59d009 is: paid'. an Open status means the invoice is awaiting payment call the function later for update.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ID": {
                        "type": "string",
                        "description": "ID of an invoice, obtained in the output string of the SendInvoice function"
                    }
                },
                "required": ["ID"],
                "additionalProperties": False,
            }
        }
    }, 
    {
        "type": "function",
        "function": {
            "name": "SendMessage",
            "strict": True,
            "description": "function to send a message asynchronously to another entity. the response will come asynchronously after processing by the recipient. the function returns an indication of success of the sending",
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
                "required": ["recipientID", "message"],
                "additionalProperties": False,
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "SendInvoice",
            "strict": True,
            "description": "Generate and send an invoice customized with buyer information. if the invoice is correctly created and sent, the function returns two different string depending on the autoPayment parameter: if autoPayment is False then it returns a string messsage containing an URL for payment to be sent to the client. If autoPayment is True it will  returns a payment reference that will allow the client to perform automated payment. In both case it returns the invoice ID to keep in order to check the status of the payment later. ",
            "parameters": {
                "type": "object",
                "properties": {
                    "clientInfo_Email": {
                        "type": "string",
                        "description": "email adress of the client, mandatory information.",
                    }
                    ,
                    "currency": {
                        "type": "string",
                        "enum": ["ETH-sepolia"],
                        "description": "currenty of the transaction. only ETH-sepolia is supported for now. mandatory information. ask if not provided ",
                    }
                     ,
                    "price": {
                        "type": "number",
                        "description": "amount in currency required to deliver the service. mandatory information. ask if not provided",
                    }
                    ,
                    "serviceName": {
                        "type": "string",
                        "description": "very short string describing the provided custom service.",
                    }
                     ,
                    "autoPayment": {
                        "type": "boolean",
                        "description": "set to True if the client ask for the payment reference. Otherwise, a URL for manual payment will be provided.",
                    }
                },
                "required": ["clientInfo_Email","currency","price","serviceName", "autoPayment"],
                "additionalProperties": False,

            },
            
        }
    }
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
    return f"Message Sent to {recipientID}"


# AUTOGEN : AI instantiation - Instance will be created on the OpenAI server. in the current implementation, it is deleted as the program terminates. 
gpt_assistant = GPTAssistantAgent(
    name="Haiku Service Provider",
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
        "SendInvoice" : IM.GenerateAndSendInvoice,
        "CheckInvoiceStatus" :IM.CheckInvoiceStatus
    }
)


# Initialize Redis connexion to access message channels 
r = redis.Redis(host='localhost', port=6379, db=0)
# Log message to build a conversation history and monitor it on a web interface 
def log_to_redis(agent, message):
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

# processing logic for response and action based on AI generated text
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
       
    if (len(messageFromAItoProcess)>=2) and 'Internal Message'.lower() not in messageFromAItoProcess.lower():
        query_openai("if this message is meant to be sent to another AI, use the SendMessage tool and check that the case sensitive AI ID is correct, else start your sentence with 'Internal Message: '.  please remember this information")
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
        # new message receiveded
        print("new message received")
        newMessage = r.rpop(f'{ia_ID}_queue').decode('utf-8')
        print(newMessage)
        # response
        response_text = query_openai(newMessage)
        MessageProcessing(response_text)
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
scheduler.add_job(poll, 'interval', seconds=3)  # Poll every 1 seconds
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
    app.run(port=5001)
    #