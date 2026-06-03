import fs from 'node:fs/promises';
import path from 'node:path';

const repoRoot = path.resolve(process.cwd(), '..');
const generatedRoot = path.join(repoRoot, 'generated');
const entriesRoot = path.join(generatedRoot, 'entries');
const indexesRoot = path.join(generatedRoot, 'indexes');

export type BookPerson = {
  personCode?: string;
  name: string;
  nameEn?: string;
  role?: string;
  avatarPath?: string;
  profileLink?: string;
  notes?: string;
};

export type BookReview = {
  source?: string;
  author?: string;
  date?: string;
  content?: string;
  url?: string | null;
  title?: string | null;
  rating?: string | number;
  votes?: number;
};

export type BookRecord = {
  id: string;
  module: 'book';
  submodule?: null;
  schemaType?: 'book';
  path?: string;
  title: string;
  originalTitle?: string;
  otherTitles?: string[];
  isbn?: string;
  year?: number;
  country?: string;
  language?: string;
  wordCount?: number;
  publisher?: string;
  publishDate?: string;
  pages?: number;
  price?: string;
  binding?: string;
  format?: string;
  edition?: string;
  synopsis?: { text?: string; note?: string };
  story?: { text?: string };
  authors?: BookPerson[];
  translators?: BookPerson[];
  genre?: string[];
  tags?: string[];
  scores?: Record<string, number>;
  doubanRating?: number;
  goodreadsRating?: number;
  openlibraryRating?: number;
  images?: {
    cover?: string;
    covers?: Record<string, string>;
    assetDir?: string;
  };
  reviews?: BookReview[];
  quotes?: Array<{ text: string; source?: string; note?: string }>;
  excerpts?: Array<{ content: string; note?: string; votes?: number; url?: string | null }>;
  series?: { id?: string; title: string; order?: number } | null;
  similar?: Array<{ id?: string; title: string; year?: number; rating?: number }>;
  sameAuthor?: Array<{ id?: string; title: string; year?: number; rating?: number }>;
  links?: Record<string, string | null>;
  createdAt?: string;
  updatedAt?: string;
  status?: string;
};

export type BookListIndexItem = {
  id: string;
  path: string;
  title: string;
  originalTitle?: string | null;
  year?: number | null;
  coverUrl: string;
  aggregateRating: number | null;
  authorNames: string | null;
  translatorNames: string | null;
  genre: string[];
  tags: string[];
  publisher: string | null;
  publishDate: string | null;
  pages: number | null;
  binding: string | null;
  synopsis: string | null;
};

export type ArchiveBook = BookRecord & {
  path: string;
  coverUrl: string;
  coverGallery: Array<{ source: string; url: string }>;
  aggregateRating: number | null;
  authorNames: string;
  translatorNames: string;
  yearLabel: string;
  publishInfoLabel: string;
  tags: string[];
};

function buildBookPath(book: Pick<BookRecord, 'id'>) {
  return `/book/${book.id}`;
}

function buildCoverUrl(book: Pick<BookRecord, 'id' | 'images'>) {
  const cover = book.images?.cover;
  if (!cover) {
    return '/assets/poster-placeholder.svg';
  }

  return `/assets/book/${book.id}/${cover}`;
}

function buildCoverGallery(book: Pick<BookRecord, 'id' | 'images'>) {
  const covers = Object.entries(book.images?.covers ?? {});
  return covers
    .map(([source, file]) => ({
      source,
      url: `/assets/book/${book.id}/${file}`
    }));
}

function dedupe(values: string[]) {
  return [...new Set(values.filter(Boolean))];
}

function computeBookAggregateRating(book: BookRecord): number | null {
  const scores = book.scores ?? {};
  const values = [
    scores.douban,
    scores.goodreads,
    scores.openlibrary,
    scores.avg,
    book.doubanRating,
    book.goodreadsRating,
    book.openlibraryRating
  ];
  const valid = values.filter((value): value is number => typeof value === 'number' && Number.isFinite(value));

  if (!valid.length) {
    return null;
  }

  return Math.round((valid.reduce((sum, value) => sum + value, 0) / valid.length) * 10) / 10;
}

function normalizeBook(book: BookRecord): ArchiveBook {
  const authorNames = (book.authors ?? []).map((person) => person.name).join(' / ');
  const translatorNames = (book.translators ?? []).map((person) => person.name).join(' / ');
  const publishFacts = [book.publisher, book.publishDate, book.binding, book.pages ? `${book.pages} 页` : '']
    .filter(Boolean)
    .join(' · ');

  return {
    ...book,
    path: book.path || buildBookPath(book),
    coverUrl: buildCoverUrl(book),
    coverGallery: buildCoverGallery(book),
    aggregateRating: computeBookAggregateRating(book),
    authorNames,
    translatorNames,
    yearLabel: book.year ? String(book.year) : '年份待补充',
    publishInfoLabel: publishFacts || '出版信息待补充',
    tags: dedupe([...(book.tags ?? []), ...(book.genre ?? [])])
  };
}

async function loadBookEntryFile(id: string): Promise<BookRecord | null> {
  const filePath = path.join(entriesRoot, 'book', `${id}.json`);
  try {
    const raw = await fs.readFile(filePath, 'utf8');
    return JSON.parse(raw) as BookRecord;
  } catch {
    return null;
  }
}

export async function loadArchiveBooks(): Promise<ArchiveBook[]> {
  const indexPath = path.join(indexesRoot, 'book.json');
  const raw = await fs.readFile(indexPath, 'utf8');
  const indexItems = JSON.parse(raw) as BookListIndexItem[];

  const books: ArchiveBook[] = [];

  for (const item of indexItems) {
    const fullRecord = await loadBookEntryFile(item.id);
    if (fullRecord) {
      books.push(normalizeBook(fullRecord));
    }
  }

  return books.sort((left, right) => Number(right.year ?? 0) - Number(left.year ?? 0) || left.id.localeCompare(right.id));
}

export async function loadArchiveBookById(id: string): Promise<ArchiveBook | null> {
  const record = await loadBookEntryFile(id);
  if (!record) {
    return null;
  }
  return normalizeBook(record);
}

export async function loadAllBookIds(): Promise<string[]> {
  const indexPath = path.join(indexesRoot, 'book.json');
  const raw = await fs.readFile(indexPath, 'utf8');
  const indexItems = JSON.parse(raw) as BookListIndexItem[];
  return indexItems.map((item) => item.id);
}
