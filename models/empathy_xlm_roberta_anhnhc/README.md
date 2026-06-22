This is XLM RoBERTa training guide.

Please make sure this file is existed: data/processed/empathyempathy_annotation_template_1.csv

0. Python version: Python 3.14.6
1. Please use the models/empathy_xlm_roberta_anhnhc/requirements.txt to install requirements.
2. pull base model from HuggingFace: FacebookAI/xlm-roberta-base to the root of the project, because the notebook will include this model like this: BASE_MODEL = "xlm-roberta-base"
3. Register jupyter kernel
4. Open train_empathy_pair_cskh_anhnhc_notebook.ipynb in you IDE
5. Select registerd kernel
6. Run all and wait ~13min if your device is Macbook M1 Pro 16" (The latancy of traning process is depending on your device)