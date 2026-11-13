# GemRetouch (web version)

Auto-retouch gem photos: dust removal on the stone, healing brush, 1:1 crop, colour, stone grouping and naming.
Runs as a Streamlit app. Photos are uploaded in the browser and the result is downloaded as one zip.

## Deploy free on Streamlit Community Cloud
1. Put these files in a GitHub repository (main file: `app.py`).
2. Go to https://share.streamlit.io, sign in with GitHub, click **Create app**, pick the repository, branch `main`, main file `app.py`.
3. Click **Deploy**. The first build takes a few minutes.

The `samples/` folder holds the demo photos behind "Try it with sample photos". Delete the folder to remove that button.

## Run on your own computer
    pip install -r requirements.txt
    streamlit run app.py
