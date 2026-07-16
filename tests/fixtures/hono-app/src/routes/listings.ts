import { Hono } from 'hono'
import { listingController } from '../controllers/listingController'
import { requireAuth } from '../middleware/auth'
const app = new Hono()
app.get('/', listingController.list)
app.post('/', requireAuth, listingController.create)
export const listingRoutes = app
