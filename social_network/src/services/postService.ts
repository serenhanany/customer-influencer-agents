import { Prisma, PrismaClient } from '@prisma/client';
import { AppError } from '../utils/errors';
import { Pagination } from '../utils/pagination';
import { extractHashtags } from '../utils/text';

const prisma = new PrismaClient();

/**
 * Shared include shape for a post returned to clients: author, the original post (for quotes),
 * comments with their authors, and engagement counts. Reused across services for consistency.
 */
export const postInclude = Prisma.validator<Prisma.PostInclude>()({
  user: { select: { id: true, name: true, avatar: true, accountType: true } },
  repostOf: {
    include: { user: { select: { id: true, name: true, avatar: true, accountType: true } } },
  },
  comments: {
    include: { user: { select: { id: true, name: true, avatar: true, accountType: true } } },
    orderBy: { createdAt: 'asc' },
  },
  _count: { select: { likes: true, reposts: true, comments: true } },
});
export type PostWithRelations = Prisma.PostGetPayload<{ include: typeof postInclude }>;

/**
 * Creates a post for the given user. Parses `#hashtags` from the content and links them.
 * Optionally references an original post (`repostOfId`) to form a quote-post.
 * Throws 400 if empty or over 500 chars, 404 if the referenced original does not exist.
 */
export async function createPost(
  userId: string,
  content: string,
  repostOfId?: string | null,
): Promise<PostWithRelations> {
  const trimmed = content.trim();
  if (!trimmed) throw new AppError('Post content cannot be empty', 400);
  if (trimmed.length > 500) throw new AppError('Post content exceeds 500 characters', 400);

  if (repostOfId) {
    const original = await prisma.post.findUnique({ where: { id: repostOfId } });
    if (!original) throw new AppError('Original post not found', 404);
  }

  const tags = extractHashtags(trimmed);

  return prisma.post.create({
    data: {
      userId,
      content: trimmed,
      repostOfId: repostOfId ?? null,
      hashtags: {
        create: tags.map((tag) => ({
          hashtag: { connectOrCreate: { where: { tag }, create: { tag } } },
        })),
      },
    },
    include: postInclude,
  });
}

/**
 * Returns posts newest first with author, comments, and engagement counts.
 */
export async function getGlobalFeed(pagination: Pagination): Promise<PostWithRelations[]> {
  return prisma.post.findMany({
    orderBy: { createdAt: 'desc' },
    skip: pagination.skip,
    take: pagination.take,
    include: postInclude,
  });
}

/**
 * Returns a single post by id. Throws 404 if not found.
 */
export async function getPostById(id: string): Promise<PostWithRelations> {
  const post = await prisma.post.findUnique({ where: { id }, include: postInclude });
  if (!post) throw new AppError('Post not found', 404);
  return post;
}
