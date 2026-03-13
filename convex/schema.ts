import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // ── Vocab data (imported from SQLite) ───────────────────────────────────
  levels: defineTable({
    sqlId: v.number(),
    title: v.string(),
    originalTitle: v.optional(v.string()),
    urlId: v.string(),
  }).index("by_sql_id", ["sqlId"]),

  subcategories: defineTable({
    sqlId: v.number(),
    levelSqlId: v.number(),
    title: v.string(),
    originalTitle: v.optional(v.string()),
    urlId: v.optional(v.string()),
    position: v.optional(v.number()),
  })
    .index("by_sql_id", ["sqlId"])
    .index("by_level", ["levelSqlId"]),

  vocabularies: defineTable({
    sqlId: v.number(),
    subcategorySqlId: v.number(),
    word: v.string(),
    pronunciation: v.optional(v.string()),
    pronunciationIpa: v.optional(v.string()),
    audioUrl: v.optional(v.string()),
    meaningVi: v.optional(v.string()),
    synonyms: v.optional(v.string()),
    imageUrl: v.optional(v.string()),
  })
    .index("by_sql_id", ["sqlId"])
    .index("by_subcategory", ["subcategorySqlId"])
    .searchIndex("search_word", { searchField: "word" }),

  examples: defineTable({
    sqlId: v.number(),
    vocabSqlId: v.number(),
    exampleEn: v.optional(v.string()),
    exampleVi: v.optional(v.string()),
    audioUrl: v.optional(v.string()),
  })
    .index("by_sql_id", ["sqlId"])
    .index("by_vocab", ["vocabSqlId"]),

  // ── User data ────────────────────────────────────────────────────────────
  botUsers: defineTable({
    telegramId: v.number(),
    username: v.optional(v.string()),
    firstName: v.string(),
  }).index("by_telegram_id", ["telegramId"]),

  userWordProgress: defineTable({
    telegramId: v.number(),
    vocabId: v.number(),
    status: v.string(), // "new" | "learning" | "known"
    correctCount: v.number(),
    wrongCount: v.number(),
    lastReviewedAt: v.optional(v.number()),
  })
    .index("by_user", ["telegramId"])
    .index("by_user_vocab", ["telegramId", "vocabId"]),

  userCustomSets: defineTable({
    telegramId: v.number(),
    name: v.string(),
    vocabIds: v.array(v.number()),
  }).index("by_user", ["telegramId"]),
});
