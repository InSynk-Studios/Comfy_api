RUN WITH :

`export FLASK_ENV=production`
`gunicorn -w 4 app:app`