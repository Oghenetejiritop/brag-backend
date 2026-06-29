import os

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

prompt_instruction = """

You are a helpful assistant that answers questions using only the provided context.

Instructions:
- Use only information from the retrieved context.
- If the user asks for a summary, overview, explanation, or description, summarize the retrieved context.
- If the answer is not present in the context, reply:
  "I don't know based on the provided information."
- Do not use outside knowledge or invent facts.
"""

class RAGProcessor:
    def __init__(
        self,
        file: str,
        persist_directory: str = "chroma_db",
        prompt_instruction: str = prompt_instruction
    ):

        self.__embeddings = OpenAIEmbeddings()

        # Load existing database or build a new one
        if os.path.exists(persist_directory) and os.listdir(persist_directory):
            print("Loading existing vector database...")

            self.__db = Chroma(
                persist_directory=persist_directory,
                embedding_function=self.__embeddings,
            )

        else:
            print("Creating vector database...")

            loader = PyPDFLoader(file)
            docs = loader.load()

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=150,
            )

            split_docs = splitter.split_documents(docs)

            self.__db = Chroma.from_documents(
                documents=split_docs,
                embedding=self.__embeddings,
                persist_directory=persist_directory,
            )


        # Retriever using MMR
        retriever = self.__db.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 4,
                "fetch_k": 20,
            },
        )

        prompt_instruction = self.__set_prompt_instruction(prompt_instruction)
        prompt = ChatPromptTemplate.from_template(prompt_instruction)

        self.__llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
        )

        self.__rag_chain = (
            {
                "context": retriever | self.__format_docs,
                "question": RunnablePassthrough(),
            }
            | prompt
            | self.__llm
            | StrOutputParser()
        )

    def __format_docs(self, docs):
        """Format retrieved documents with page metadata."""

        formatted = []

        for doc in docs:
            page = doc.metadata.get("page", "Unknown")
            formatted.append(
                f"Page {page + 1}\n"
                "--------------------\n"
                f"{doc.page_content}"
            )

        return "\n\n".join(formatted)

    def __set_prompt_instruction(self, prompt: str):
        return prompt + """

Context:
{context}

Question:
{question}
"""

    def generate_response(self, query: str):
        return self.__rag_chain.invoke(query)
