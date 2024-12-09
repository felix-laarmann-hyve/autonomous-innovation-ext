import os
import toml

from langchain_openai import ChatOpenAI
from langchain import hub
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.schema import HumanMessage, AIMessage, SystemMessage  # Import message classes
from langchain_core.callbacks import BaseCallbackHandler  # Ensure this import is included

import streamlit as st
from langchain_community.callbacks.streamlit import StreamlitCallbackHandler

class MyCustomHandler(BaseCallbackHandler):
    def on_chain_start(self, serialized, inputs, **kwargs):
        st.info("chain started")

st.set_page_config(page_title="HYVE AutoInno Pipeline", page_icon="bee")

hide_st_style = """
    <style>    
    footer {visibility: hidden;}    
    </style>
"""

st.markdown(hide_st_style, unsafe_allow_html=True)

st_callback = StreamlitCallbackHandler(st.container())

# Load config and set environment variable for Tavily API key
os.environ['TAVILY_API_KEY'] = st.secrets["Tavily"]["api_key"]
os.environ['LANGCHAIN_TRACING_V2'] = st.secrets["Langchain"]["LANGCHAIN_TRACING_V2"]
os.environ['LANGCHAIN_API_KEY'] = st.secrets["Langchain"]["LANGCHAIN_API_KEY"]
os.environ['LANGCHAIN_ENDPOINT'] = st.secrets["Langchain"]["LANGCHAIN_ENDPOINT"]
os.environ['LANGCHAIN_PROJECT'] = st.secrets["Langchain"]["LANGCHAIN_PROJECT"]

os.environ['OPENAI_API_KEY'] = st.secrets["OpenAI"]["OPENAI_API_KEY"]

os.environ['UN_ADMIN'] = st.secrets["Credentials"]["UN_ADMIN"]
os.environ['PW_ADMIN'] = st.secrets["Credentials"]["PW_ADMIN"]
os.environ['UN_USER'] = st.secrets["Credentials"]["UN_USER"]
os.environ['PW_USER'] = st.secrets["Credentials"]["PW_USER"]


# Session state handling for API key
if 'pw_submitted' not in st.session_state:
    st.session_state['pw_submitted'] = False

if not st.session_state['pw_submitted']:
    user = st.text_input("User:", value="")
    pw = st.text_input("Password:", type="password", value="")
    submit_key = st.button("Login")

    if submit_key and user and pw:
        # st.session_state['api_key'] = api_key
        if (user == os.environ['UN_USER'] and pw == os.environ['PW_USER']) or (user == os.environ['UN_ADMIN'] and pw == os.environ['PW_ADMIN']):
            st.session_state['pw_submitted'] = True
            st.rerun()  # Rerun the app to reflect the state change
        else:
            st.warning("Wrong credentials")

if ('pw_submitted' in st.session_state) and st.session_state['pw_submitted'] == True:

    # Initialize LLM and agents
    llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
    search = TavilySearchResults()
    tools = [search]
    prompt = hub.pull("hwchase17/openai-functions-agent")
    research_agent = create_tool_calling_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=research_agent, tools=tools, verbose=True, handle_parsing_errors=True)

    default_system_messages = [
        "You are an AI specialized in innovation processes for products and services. Your task is to guide through the entire innovation process from research to concept creation. You are equipped with a search tool. You conclude every task by suggesting a next step. The user inputs an innovation challenge:",
        "Start with 1.1 researching trends in the given field and format the results as a table.",
        "Then proceed with 1.2 researching products and competitors in the given field and format the results as a table.",
        "1.3 research painpoints for each of the relevant products and format the results as a table. Use product reviews and Reddit for this research.",
        "Next, 2.1 evaluate the painpoints by impact.",
        "2.2 for the top 5 painpoints, define a How Might We Statement.",
        "Then, 3.1 dive into ideation and suggest 10 ideas for each painpoint using ideation methods like SCAMPER, TRIZ, and analogy thinking.",
        "3.2 Evaluate the ideas by potential and effort and format the results in a table.",
        "For the top idea, 4.1 create a persona.",
        "4.2 Create a concept description mentioning the target group, value, and idea description.",
        "4.3 Suggest a roadmap for next steps including advice on how to prototype and test the idea.",
        "Finally, 5.1 generate a briefing of the most promising idea. This briefing should outline the core concept and features to generate a web application. Please provide your output as code with no more than 400 words, following this structure: Hey Claude, based on the following briefing, create a React webpage. The webpage should have exceptional visual design using glassmorphic design, outstanding aesthetics, a modern color scheme and mind-blowing animations. Implement a top menu bar to navigate between the subpages. Briefing: [Paste Briefing here]"
    ]
    
    if 'system_messages' not in st.session_state:
        st.session_state['system_messages'] = default_system_messages
        st.session_state['current_prompt_index'] = 0  # Initialize prompt index
        st.session_state['initial_input_added'] = False  # Track if user input was added to the first message
        st.session_state['chat_history'] = []  # Initialize chat history

    chat_history = [
        SystemMessage(content=msg) for msg in st.session_state['system_messages']
    ]
    chat_history.extend([
        HumanMessage(content="You are my innovation expert. I will give you a topic and you will conduct the entire innovation process from user, trend and tech research to ideation and concept creation."),
        AIMessage(content="Now provide your topic so I can dive into the research!")
    ])

    message_history = ChatMessageHistory()
    message_history.messages = chat_history

    agent_with_chat_history = RunnableWithMessageHistory(
        agent_executor,
        lambda session_id: message_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )

    st.title('🐝 HYVE AutoInno Pipeline')

    # Toggle to show/hide the message editing menu
    if 'edit_menu' not in st.session_state:
        st.session_state['edit_menu'] = False

    if st.button("Setup agent"):
        st.session_state['edit_menu'] = not st.session_state['edit_menu']

    if st.session_state['edit_menu']:
        st.subheader("Edit System Messages")

        for i, message in enumerate(st.session_state['system_messages']):
            st.session_state['system_messages'][i] = st.text_area(f"Message {i + 1}", message, key=f"msg_{i}")

        if st.button("Add New Message"):
            st.session_state['system_messages'].append("")
            st.rerun()  # Rerun the app to reflect the state change

        if st.button("Remove Last Message"):
            if st.session_state['system_messages']:
                st.session_state['system_messages'].pop()
                st.rerun()  # Rerun the app to reflect the state change

        if st.button("Update Messages"):
            st.success("System messages updated successfully!")     
            st.session_state['edit_menu'] = False
            st.rerun()  # Rerun the app to reflect the state change

    # Form to enter the initial challenge
    with st.form('my_form'):
        initial_input = st.text_area('Enter your Innovation Challenge:', 'future digital services in automotive')
        submitted = st.form_submit_button('Submit')

    if submitted:
        st.session_state['current_prompt_index'] = 0  # Reset prompt index on new submission
        st.session_state['initial_input'] = initial_input  # Store the initial input
        st.session_state['process_started'] = True  # Indicate that the process should start
        st.session_state['initial_input_added'] = False  # Reset the flag to ensure user input is added only once
        st.session_state['chat_history'] = []  # Reset chat history on new input
        st.rerun()  # Rerun the app to reflect the new input

    # Process prompts one by one if the process has started
    if st.session_state.get('process_started', False):

        # Add the user input to the first system message only once
        if not st.session_state['initial_input_added']:
            st.session_state['system_messages'][0] += f" {st.session_state['initial_input']}"
            st.session_state['initial_input_added'] = True

        message_history = ChatMessageHistory()

        for current_prompt in st.session_state['system_messages']:
            message_history.messages.append(SystemMessage(content=current_prompt))
            
            st.info(f"Executing: {current_prompt}")

            agent_with_chat_history = RunnableWithMessageHistory(
                agent_executor,
                lambda session_id: message_history,
                input_messages_key="input",
                history_messages_key="chat_history",
            )

            result = agent_with_chat_history.invoke(
                {"chat_history": message_history.messages, "input": current_prompt},
                config={"configurable": {"session_id": "<foo>"},"callbacks":[st_callback]}
            )

            with st.chat_message("assistant"):
                st.write(result.get('output'))

        st.success("Innovation project executed!")
    