# supermarkt-price-dashboard

A demo dashboard for comparing the groceries' prices in the local supermarket.

## Project Structure

```
supermarket-price-dashboard/
├── frontend/          ← React app (deployed to Vercel)
│   └── src/
│       ├── components/
│       ├── pages/
│       ├── hooks/
│       └── utils/
├── backend/           ← Express.js API (deployed to Railway)
│   └── src/
│       ├── routes/
│       ├── controllers/
│       ├── middleware/
│       └── db/
├── scraper/           ← Python scraper (runs via GitHub Actions)
│   ├── spiders/
│   └── pipelines/
├── docker-compose.yml ← Spin up local DB + Redis instantly
├── .gitignore
└── README.md
```

## Initialise the Reac app

Inside the project, run: 
`cd frontend` 
`npm create vite@latest . -- --template react` 
`npm install` 

Then install all the libraries: 
`npm install \ react-router-dom \ @tanstack/react-query \ axios \ recharts \ lucide-react` 

`npm install -D \ tailwindcss \ postcss \ autoprefixer` 

`npx tailwindcss init -p` **If error detects, please refer to the Note below** 

### Notes

> Error detection: `npm error could not determine executable to run` 
> This may be caused by that the Tailwind CLI isn't found via **npx** with the version installed. 
> Run `./node_modules/.bin/tailwindcss init -p` instead. **OR** 
> try reinstalling Tailwind with an explicit version that includes the CLI: 
> `npm install -D tailwindcss@3 postcss autoprefixer` 
> `./node_modules/.bin/tailwindcss init -p` 
