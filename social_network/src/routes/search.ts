import { Router, Request, Response, NextFunction } from 'express';
import { search } from '../services/searchService';
import { sendSuccess } from '../utils/response';
import { parsePagination } from '../utils/pagination';

const router = Router();

/**
 * GET /api/search?q=...
 * Searches users, posts, and hashtags. Paginated per result type.
 */
router.get('/', async (req: Request, res: Response, next: NextFunction) => {
  try {
    const q = String(req.query['q'] ?? '');
    const results = await search(q, parsePagination(req.query));
    sendSuccess(res, results);
  } catch (err) {
    next(err);
  }
});

export default router;
