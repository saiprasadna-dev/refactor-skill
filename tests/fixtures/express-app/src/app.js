const express = require('express')
const searchRouter = require('./routes/search')
const app = express()
app.use('/api', searchRouter)
