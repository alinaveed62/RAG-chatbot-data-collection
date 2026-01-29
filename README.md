# RAG-chatbot-data-collection

Keats URL: https://keats.kcl.ac.uk/login/index.php


A RAG chatbot for answering student queries. - variant 2
Project description:	
What is this project about?
Retrieval Augmented Generation (RAG) is a technique whereby a Large Language Model (LLM) is combined with an information retrieval system and an external information source to generate answers to queries. The external information source is, normally, a substantial document or set of documents divided into shorter chunks, with each chunk addressing a specific topic. Given a query, a RAG chatbot employs information retrieval techniques to retrieve the chunks that are most similar to the query. The query is then combined with the retrieved information sources to generate a prompt for an LLM to answer the query.
RAG is a particularly suitable approach for developing domain specific Q&A chatbots. It can produce accurate, domain-specific answers, using foundation models without expensive machine learning. As domain knowledge changes, the information source can be replaced by a new one with relatively little cost (compared to pre-training or fine-tuning a foundation model).
The objective of this project is to produce a RAG chatbot that can answer a particular category of student queries accurately. The variants of the project differ primarily in the information source that is employed. Consequently, each RAG chatbot variant will aim to serve a different subset of student queries.
Important: The techniques you will be using in the development of this system can provide incorrect advice. You must take reasonable steps to ensure that prospective end-users do not use the system to receive advice.
Who is this project for?
This project is suitable for an Artificial Intelligence (AI) student or a Computer Science (CS) student with a strong interest in Artificial Intelligence. The project includes both AI and CS challenges.
The first challenge you will encounter is to clean your information source into a usable collection of document chunks. The nature of this challenge differs considerably from project to project. It is critical that your solution employs a fully automated approach to data preparation so that new knowledge can be slotted in as necessary without manual work.
The second challenge is to build a working RAG chatbot. Normally, you will start to implement a relatively standard pipeline with pre-trained models. If you are inclined to engage in the labour-intensive task of producing your own dataset, you may choose to fine-tune existing models. However, this is very much a stretch objective to be completed only after completing the third challenge.
The third challenge is to evaluate your initial RAG chatbot, and different variants of it. An evaluation will typically include an empirical study into the accuracy of the retrieval system. An assessment of the answer quality of different models should consider the size and resource demands of the models that are employed.
If you believe these are suitable challenges for you, and you are prepared to commit to the necessary independent studying you will need to do to tackle these challenges, then this is a suitable project for you.
You may or may not build a web application as an interface to your chatbot. Of course, this will be a tiny application, requiring only two screens: (i) a screen with a textbox and button to submit a question, and (ii) a screen to show the answer. Provided you could produce a RAG relatively quickly (by January), you could extend this basic system with one that logs questions, answers, and user feedback for evaluation. However, this project has *no* scope for significant web development.
What technology stack and resources does this project need?
Python is the "lingua franca" of this type of project. I recommend that you use certain libraries, including but not limited to Pytorch (or tensorflow -- but I recommend Pytorch for this project), transformers (from Hugging Face), faiss (or any other vector database). You will also need packages to aid with data cleaning and preparation, and to interface with the LLM of your choice.
I recommend you complete all practical work on Google Colab (Free Tier). This gives you free access to an online Python notebook with access to GPU and TPU resources. The free service comes with a few minor inconveniences, such as fluctuating availability those the resources and time restrictions on notebooks. With a little planning and risk avoidance (e.g. not leaving critical computational work to the day before the deadline), these can be overcome.
If your project requires it, we can apply to get you access to King's HPC infrastructure. There is *no* budget for access to commercial LLMs, such as the paid-for GPT models.
If you intend to build a web-based user interface for your system, Flask is sufficient. Given that such a user interface will not be a significant contribution compared to the RAG, it is advisable to keep it simple.
What are the variants of this project?
The different variants of the project employ a different information source. Therefore, they seek to answer a different range of questions.


Variant 2: Informatics Student Handbook
This variant seeks to answer queries based on the Student Handbook of the Department of Informatics. Example questions include: "Do I have to attend all my lectures?", "What are the office hours of my project supervisor, Dr Jeroen Keppens, and where is his office?", "How can I become a student rep in the department?". This information source is available to you as a range of information pages available via KEATS.


I strongly recommend you start this project with practical learning. The College's LinkedIn Learning subscription is a fantastic resource for a practical course on RAG. There are several and I recommend you pick one that suits your starting point. If you have never used Pytorch before, a practical course on Pytorch would be useful. This will help you understand how to tackle the second challenge of this project, and recognise what the output for the first challenge needs to be.
By building a RAG, you will develop an intuitive, if limited, understanding of how works. You can deepen your understanding later by searching for papers on specific topics.
What is your approach to supervision?
My view on UG/PGT project supervision is that, once you are assigned a particular project variant, the project you own it and are responsible for it (Apart from this project description: it remains mine, so do not copy-paste it straight in to your slides or report). I will be suggesting what I believe to be the most fruitful possible directions you can take and I will provide feedback on work you share with me in a timely manner. You are free to choose your own direction, however, as long as your actions do not breach College regulations and policies.
Unless the department has agreed a set of reasonable adjustments concerning project supervision, I follow the standard supervision approach. This consists of five group meetings, and two individual meetings at pre-scheduled periods of the academic year. In addition to this, can contact me via email if you have *small* questions/queries. You can also visit me during my office hours.
I hold office hours during term time. To see me during office hours, please book a 10 minute sessions during my office hours.
Can I get a high mark for this project?
I do not know what mark you can get for this project, but the project brief does not prevent this.
What do I need to do to get an A for this project?
The premise of this (not uncommon) question is that there is set of action such that, if you take them, you are guaranteed a high mark. This premise is incorrect. All projects are assessed against levels of attainment set out in the marking criteria. While I will suggest to you what I believe to be the most promising direction for your project, I can never offer any guarantees that it will lead to very high levels of attainment.
Deliverables:	
Non-standard hardware/software required:	No
Project status:	Allocated
Student name:	NAVEED, MUHAMMAD
