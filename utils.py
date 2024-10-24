import os
import requests
import pandas as pd

from xml.etree import ElementTree
from bs4 import BeautifulSoup

from openai import AzureOpenAI


BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov/"


class Literature:
    def __init__(self, query):
        self.query = query
        
    def search_pubmed(self):
        max_results=2
        search_url = f"{BASE_URL}esearch.fcgi"
        params = {'db': 'pubmed', 'term': self.query, 'retmax': max_results, 'retmode': 'xml'}
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        tree = ElementTree.fromstring(response.content)
        return [uid.text for uid in tree.findall(".//Id")]


    def fetch_details(self, uids):
        fetch_url = f"{BASE_URL}efetch.fcgi"
        params = {'db': 'pubmed', 'id': ','.join(uids), 'retmode': 'xml'}
        response = requests.get(fetch_url, params=params)
        response.raise_for_status()
        return response.content

    def parse_article_details(self, uids, xml_data):
        tree = ElementTree.fromstring(xml_data)
        articles = []
        for i, article in enumerate(tree.findall(".//PubmedArticle")):
            details = {
                'title': article.findtext(".//ArticleTitle"),
                'abstract': article.findtext(".//AbstractText"),
                'journal': article.findtext(".//Journal/Title"),
                'pub_date': article.findtext(".//PubDate/Year"),
                'uid': uids[i]
            }
            articles.append(details)
        return articles

    def fetch_pubmed_article(self, uid):
        pubmed_url = f"{PUBMED_BASE_URL}{uid}/"
        response = requests.get(pubmed_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')

        title = soup.find('meta', {'name': 'citation_title'})['content'] if soup.find('meta', {'name': 'citation_title'}) else 'No title available'
        abstract_meta = soup.find('meta', {'name': 'citation_abstract'})
        abstract = abstract_meta['content'] if abstract_meta else 'No abstract available'
        
        journal = soup.find('meta', {'name': 'citation_journal_title'})['content'] if soup.find('meta', {'name': 'citation_journal_title'}) else 'No journal available'
        pub_date = soup.find('meta', {'name': 'citation_publication_date'})['content'] if soup.find('meta', {'name': 'citation_publication_date'}) else 'No publication date available'

        return {
            'title': title,
            'abstract': abstract,
            'journal': journal,
            'pub_date': pub_date,
            'uid': uid
        }


def get_genai_response(articles):
    list_article = []

    context = "you are health care expert!"
    context_str = """Identify if this article has potential adverse events or product quality complaints, and if it has an Adverse event or PQC, extract those. Also, see if there is positive attribution to the drug (highlight the same):
        has anywhere in the abstract does it mentions or has any implication stated that the drug has led to the event?"""
   
    for article in articles:
        prompt = article['abstract']

        client = AzureOpenAI(
            azure_endpoint='https://ajayopenaiinstance.openai.azure.com/',
            api_key='24c67f9f1f844378980152d5ce05ae63',
            api_version="2024-02-15-preview"
        )

        # Send request to Azure OpenAI model
        response = client.chat.completions.create(
            model="mygpt4",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt + '\n' + context_str }
            ]
        )
        
        first_response = response.choices[0].message.content

        event_data = check_adverse_event(first_response, client)
        # print("event_data++", event_data)
        adverse_events,product_quality_complaints,positive_attribution,drug_implications = article_analaysis(first_response, client)
        # print("adverse_events", adverse_events)
        # print("product_quality_complaints", product_quality_complaints)
        
        adverse_flag = ''
        nonadverse_flag = ''
        positive_flag = ''
        negative_flag = ''

        text = event_data
        text = text.replace('*','')  
        text = text.replace('#','')  
        lines = text.split('\n')  
        for i, line in enumerate(lines):
                
            parts = line[2:].split(': ')
            if len(parts) == 2:  
                flag, value = parts
                # print('flag++++++++++++++', flag)
                # print('value++++++', value)
                if flag == "Adverse Event":
                    adverse_flag = value
                elif flag == "Non Adverse Event":
                    nonadverse_flag = value
                elif flag == "Positive Attribution":
                    positive_flag = value
                elif flag == "Negative Attribution":
                    negative_flag = value


        detail_article = {
            'UID': article['uid'],
            'Title': article['title'],
            'Journal': article['journal'],
            'Pub Date': article['pub_date'],
            'Abstract': article['abstract'],
            'Article Analysis': first_response,
            'Adverse Flag': adverse_flag,
            'Nonadverse Flag': nonadverse_flag,
            "Positive Flag": positive_flag,
            "Negative Flag": negative_flag,
            'Adverse Events':  adverse_events,
            'Product Quality Complaints (PQC)': product_quality_complaints,
            'Positive Attribution to the Drug': positive_attribution,
            'Implication of the Drug Leading to Events':drug_implications,          
        }

        list_article.append(detail_article)

    df = pd.DataFrame(list_article)

    os.makedirs('Reports', exist_ok=True)
    df.to_excel(os.path.join('Reports', 'All_Literature.xlsx'), index=False)
    
    return list_article

    
def check_adverse_event(response_data, client):
    context = "you are health care expert!"
    context_str = """Provide Y or N for each below flag using above article.
        Adverse Event   
        Non Adverse Event   
        Positive Attribution    
        Negative Attributionnt"""

    # Send request to Azure OpenAI model
    response = client.chat.completions.create(
        model="mygpt4",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": response_data + '\n' + context_str}
        ]
    )
    
    event_data = response.choices[0].message.content
    # print("response_data+++++22222222+++++++++", response_data)
    return event_data


def article_analaysis(response_data, client):
    context = "you are health care expert!"
    condation = """List all the Adverse Events, drug, device, vaccine realetd Product Quality Complaints, 
        Positive Attributions and Implication of DrugLeading to Events 
        septerately """

     # Send request to Azure OpenAI model
    response = client.chat.completions.create(
        model="mygpt4",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": response_data + '\n' + condation}
        ]
    )
    response_data = response.choices[0].message.content

    # print('response_data+++++++++++++', response_data)
    # Lists to store extracted data
    adverse_events = []
    product_quality_complaints = []
    positive_attribution = []
    drug_implications = []
    # first_sentence = []
    # last_sentence = []

    text = response_data
    # print("text+++++++++++++", text)
    text = text.replace('*','')  
    text = text.replace('#','')  
    lines = text.split('\n')  
    
    for i, line in enumerate(lines):  
        if 'Adverse Events:' in line:  
            adverse_events.append(lines[i+1].strip())  
        elif 'Product Quality Complaints (PQC):' in line:  
            product_quality_complaints.append(lines[i+1].strip()) 
        elif 'Positive Attributions' in line:
            positive_attribution.append(lines[i+1].strip())
        elif 'Implication of Drug Leading to Events' in line:
            drug_implications.append(lines[i+1].strip())

    # Printing the results
    # print("Adverse Events:", adverse_events)
    # print("Product Quality Complaints (PQC):", product_quality_complaints)
    # print("Positive Attribution to the Drug:", positive_attribution)
    # print("Implication of the Drug Leading to Events:", drug_implications)
    # print("First Sentence:", first_sentence)
    # print("Last Sentence:", last_sentence)

    return adverse_events,product_quality_complaints,positive_attribution,drug_implications  

