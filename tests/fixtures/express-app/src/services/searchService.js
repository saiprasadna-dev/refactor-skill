const knex = require('knex')
exports.doSearch = async (q) => knex('products').where('name', 'like', q)
