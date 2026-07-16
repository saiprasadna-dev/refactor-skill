const router = require('express').Router()
const { doSearch } = require('../services/searchService')
router.get('/search', async (req, res) => res.json(await doSearch(req.query.q)))
module.exports = router
