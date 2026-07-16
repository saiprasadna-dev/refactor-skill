import { Hono } from 'hono'
import { listingRoutes } from './routes/listings'
const app = new Hono()
app.route('/listings', listingRoutes)
export default app
