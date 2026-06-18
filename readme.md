# AI resume screener

AN AI powered system built with fastAPI that analyse resumes in pdf format. it extract key information such as skills, work experience, score and provide structured result.

## Features
- upload resumes in pdf format
- background AI-based analysis using FastAPI 
- JSON output with extracted details
- easy deployment with 'uvicorn'

## Installation

clone the repository and install the dependencies:

''' bash
git clone https://github.com/joyjit-developer/YUPCHA_Ai_resume_screener.git

cd YupCHA_AI_resume_screener
pip install -r requirement.txt


## Usages

start FastAPI server 

'''bash uvicorn main:app --reload

access the interective API at

http://127.0.0.1:8000


## Project structure

resume screener
|-- main.py ## fastapi entry point
|--model.py ## AI model used for analysing
|--perser.py ##extract details from pdf
|database.py ## store data extracted from pdf
|screener.py ## display the extracted data based on the requirements

## API endpoint

    Post - upload a PDF resume and trigger background analysis

    get - retrieve the structured analysis data

## Tech Stack 

 |-- FastAPI - web framework
 |-- uvicorn - ASGI server
 |-- pdfplumber - PDF parsing
 |-- postgraSQL - storing the retrival data