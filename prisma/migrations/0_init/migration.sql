-- CreateTable
CREATE TABLE "works" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "module" TEXT NOT NULL,
    "submodule" TEXT,
    "schema_type" TEXT NOT NULL,
    "title" TEXT NOT NULL,
    "title_original" TEXT,
    "other_titles" TEXT,
    "year" INTEGER,
    "country" TEXT,
    "language" TEXT,
    "total_time" INTEGER,
    "studio" TEXT,
    "release_dates" TEXT,
    "quotes" TEXT,
    "scores" TEXT,
    "episode_count" INTEGER,
    "episode_time" INTEGER,
    "episodes_story" TEXT,
    "introduction" TEXT,
    "story" TEXT,
    "external_source" TEXT,
    "images" TEXT,
    "videos" TEXT,
    "comments" TEXT,
    "soundtrack" TEXT,
    "related" TEXT,
    "characters" TEXT,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "person" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "person_id" TEXT NOT NULL UNIQUE,
    "name" TEXT NOT NULL,
    "name_en" TEXT,
    "source_ids" TEXT,
    "avatar_path" TEXT,
    "tmdb_avatar_path" TEXT,
    "douban_avatar_path" TEXT,
    "profile_link" TEXT,
    "intro" TEXT
);

-- CreateTable
CREATE TABLE "work_person" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "work_id" TEXT NOT NULL,
    "person_id" INTEGER NOT NULL,
    "department" TEXT NOT NULL,
    "role" TEXT,
    "character" TEXT,
    "character_en" TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_primary" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "work_person_work_id_fkey" FOREIGN KEY ("work_id") REFERENCES "works" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "work_person_person_id_fkey" FOREIGN KEY ("person_id") REFERENCES "person" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "category" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "group" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "module" TEXT,
    "submodule" TEXT,
    "order" INTEGER NOT NULL DEFAULT 0,
    "enabled" BOOLEAN NOT NULL DEFAULT true
);

-- CreateTable
CREATE TABLE "work_category" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "work_id" TEXT NOT NULL,
    "category_id" INTEGER NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "work_category_work_id_fkey" FOREIGN KEY ("work_id") REFERENCES "works" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "work_category_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "category" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "schema_migrations" (
    "version" TEXT NOT NULL PRIMARY KEY,
    "applied_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- CreateTable
CREATE TABLE "books" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "title" TEXT NOT NULL,
    "title_original" TEXT,
    "other_titles" TEXT,
    "isbn" TEXT,
    "year" INTEGER,
    "country" TEXT,
    "language" TEXT,
    "word_count" INTEGER,
    "publisher" TEXT,
    "publish_date" TEXT,
    "pages" INTEGER,
    "price" TEXT,
    "binding" TEXT,
    "format" TEXT,
    "edition" TEXT,
    "summary" TEXT,
    "story" TEXT,
    "quotes" TEXT,
    "excerpts" TEXT,
    "series_id" TEXT,
    "series_order" INTEGER,
    "scores" TEXT,
    "external_source" TEXT,
    "images" TEXT,
    "reviews" TEXT,
    "related" TEXT,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL,
    CONSTRAINT "books_series_id_fkey" FOREIGN KEY ("series_id") REFERENCES "book_series" ("id") ON DELETE SET NULL ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "book_series" (
    "id" TEXT NOT NULL PRIMARY KEY,
    "name" TEXT NOT NULL,
    "name_original" TEXT,
    "book_count" INTEGER,
    "summary" TEXT,
    "images" TEXT,
    "status" TEXT NOT NULL DEFAULT 'draft',
    "created_at" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updated_at" DATETIME NOT NULL
);

-- CreateTable
CREATE TABLE "book_person" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "book_id" TEXT NOT NULL,
    "person_id" INTEGER NOT NULL,
    "role" TEXT NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    "is_primary" BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT "book_person_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "books" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "book_person_person_id_fkey" FOREIGN KEY ("person_id") REFERENCES "person" ("id") ON DELETE RESTRICT ON UPDATE CASCADE
);

-- CreateTable
CREATE TABLE "book_category" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "book_id" TEXT NOT NULL,
    "category_id" INTEGER NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    CONSTRAINT "book_category_book_id_fkey" FOREIGN KEY ("book_id") REFERENCES "books" ("id") ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT "book_category_category_id_fkey" FOREIGN KEY ("category_id") REFERENCES "category" ("id") ON DELETE CASCADE ON UPDATE CASCADE
);

-- CreateIndex
CREATE INDEX "idx_works_module_submodule" ON "works"("module", "submodule");

-- CreateIndex
CREATE INDEX "idx_works_schema_type" ON "works"("schema_type");

-- CreateIndex
CREATE INDEX "idx_works_status" ON "works"("status");

-- CreateIndex
CREATE INDEX "idx_works_year" ON "works"("year");

-- CreateIndex
CREATE INDEX "idx_person_name" ON "person"("name", "name_en");

-- CreateIndex
CREATE INDEX "idx_work_person_work_id" ON "work_person"("work_id", "order");

-- CreateIndex
CREATE INDEX "idx_work_person_person_id" ON "work_person"("person_id");

-- CreateIndex
CREATE INDEX "idx_category_scope" ON "category"("group", "module", "submodule", "order");

-- CreateIndex
CREATE INDEX "idx_category_identity" ON "category"("group", "name", "module", "submodule");

-- CreateIndex
CREATE INDEX "idx_work_category_work_id" ON "work_category"("work_id", "order");

-- CreateIndex
CREATE INDEX "idx_work_category_category_id" ON "work_category"("category_id");

-- CreateIndex
CREATE UNIQUE INDEX "work_category_work_id_category_id_key" ON "work_category"("work_id", "category_id");

-- CreateIndex
CREATE UNIQUE INDEX "books_isbn_key" ON "books"("isbn");

-- CreateIndex
CREATE INDEX "idx_books_year" ON "books"("year");

-- CreateIndex
CREATE INDEX "idx_books_status" ON "books"("status");

-- CreateIndex
CREATE INDEX "idx_book_person_book_id" ON "book_person"("book_id", "order");

-- CreateIndex
CREATE UNIQUE INDEX "book_person_book_id_person_id_role_key" ON "book_person"("book_id", "person_id", "role");

-- CreateIndex
CREATE INDEX "idx_book_category_book_id" ON "book_category"("book_id", "order");

-- CreateIndex
CREATE UNIQUE INDEX "book_category_book_id_category_id_key" ON "book_category"("book_id", "category_id");
