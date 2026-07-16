const express = require('express')
const mysql = require('mysql2')
const app = express()
const db = mysql.createConnection({})

// --- users ---
app.get('/api/users', (req, res) => { db.query('SELECT * FROM users', (e, r) => res.json(r)) })
app.get('/api/users/:id', (req, res) => { db.query('SELECT * FROM users WHERE id=?', [req.params.id], (e, r) => res.json(r[0])) })
app.post('/api/users', requireAuth, (req, res) => { db.query('INSERT INTO users SET ?', req.body, () => res.status(201).json({ok: true})) })
app.delete('/api/users/:id', requireAuth, (req, res) => { db.query('DELETE FROM users WHERE id=?', [req.params.id], () => res.json({ok: true})) })

// --- orders ---
app.get('/api/orders', requireAuth, (req, res) => { db.query('SELECT * FROM orders', (e, r) => res.json(r)) })
app.post('/api/orders', requireAuth, (req, res) => {
  const total = req.body.qty * req.body.price * 1.18  // GST business rule
  db.query('INSERT INTO orders SET ?', {...req.body, total}, () => res.status(201).json({total}))
})
app.post('/api/orders/:id/cancel', requireAuth, (req, res) => { db.query('UPDATE orders SET status="cancelled" WHERE id=?', [req.params.id], () => res.json({ok: true})) })

// --- search ---
app.get('/api/search', (req, res) => { db.query('SELECT * FROM products WHERE name LIKE ?', ['%'+req.query.q+'%'], (e, r) => res.json(r)) })

// --- reports ---
app.get('/api/reports/daily', requireAuth, (req, res) => { db.query('SELECT SUM(total) FROM orders', (e, r) => res.json(r)) })

function requireAuth(req, res, next) { if (!req.headers.authorization) return res.status(401).end(); next() }
app.listen(3000)
