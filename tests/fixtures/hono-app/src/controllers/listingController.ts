import { listActive } from '../services/listingRepo'
export const listingController = {
  list: async (c: any) => {
    const user = c.get('user')   // must NOT be detected as a route
    return c.json({ listings: await listActive(c.env.DB) })
  },
  create: async (c: any) => c.json({}, 201),
}
