import { PrismaClient } from '@prisma/client';
import { createPost, getGlobalFeed, getPostById } from '../postService';
import { AppError } from '../../utils/errors';

const prisma = new PrismaClient();
const page = { skip: 0, take: 20 };

function createUser(name: string) {
  return prisma.user.create({ data: { name } });
}

beforeEach(async () => {
  await prisma.comment.deleteMany();
  await prisma.follow.deleteMany();
  await prisma.post.deleteMany();
  await prisma.user.deleteMany();
});

afterAll(async () => {
  await prisma.$disconnect();
});

describe('createPost', () => {
  it('creates a post and returns it with author info', async () => {
    const u = await createUser('poster');
    const post = await createPost(u.id, 'Hello world!');
    expect(post.content).toBe('Hello world!');
    expect(post.user.name).toBe('poster');
  });

  it('throws 400 on empty content', async () => {
    const u = await createUser('empty');
    await expect(createPost(u.id, '   ')).rejects.toThrow(AppError);
  });

  it('throws 400 when content exceeds 500 chars', async () => {
    const u = await createUser('toolong');
    await expect(createPost(u.id, 'a'.repeat(501))).rejects.toThrow(AppError);
  });
});

describe('getGlobalFeed', () => {
  it('returns posts newest first', async () => {
    const u = await createUser('feeduser');
    await createPost(u.id, 'First');
    await createPost(u.id, 'Second');
    const feed = await getGlobalFeed(page);
    expect(feed[0]!.content).toBe('Second');
    expect(feed[1]!.content).toBe('First');
  });
});

describe('getPostById', () => {
  it('returns a post with comments', async () => {
    const u = await createUser('findpost');
    const post = await createPost(u.id, 'Find me');
    const found = await getPostById(post.id);
    expect(found.content).toBe('Find me');
  });

  it('throws 404 for a non-existent post', async () => {
    await expect(getPostById('nonexistent')).rejects.toThrow(AppError);
  });
});
