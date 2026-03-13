import { query } from "./_generated/server";
import { v } from "convex/values";

export const getLevels = query({
  args: {},
  handler: async (ctx) => {
    return await ctx.db.query("levels").collect();
  },
});

export const getSubcategoriesByLevel = query({
  args: { levelSqlId: v.number() },
  handler: async (ctx, { levelSqlId }) => {
    return await ctx.db
      .query("subcategories")
      .withIndex("by_level", (q) => q.eq("levelSqlId", levelSqlId))
      .collect();
  },
});

export const getVocabBySubcategory = query({
  args: { subcategorySqlId: v.number() },
  handler: async (ctx, { subcategorySqlId }) => {
    return await ctx.db
      .query("vocabularies")
      .withIndex("by_subcategory", (q) => q.eq("subcategorySqlId", subcategorySqlId))
      .collect();
  },
});

export const getVocabBySqlIds = query({
  args: { sqlIds: v.array(v.number()) },
  handler: async (ctx, { sqlIds }) => {
    const results = await Promise.all(
      sqlIds.map((id) =>
        ctx.db
          .query("vocabularies")
          .withIndex("by_sql_id", (q) => q.eq("sqlId", id))
          .first()
      )
    );
    return results.filter(Boolean);
  },
});

export const getVocabBySqlId = query({
  args: { sqlId: v.number() },
  handler: async (ctx, { sqlId }) => {
    return await ctx.db
      .query("vocabularies")
      .withIndex("by_sql_id", (q) => q.eq("sqlId", sqlId))
      .first();
  },
});

export const getExamplesByVocab = query({
  args: { vocabSqlId: v.number() },
  handler: async (ctx, { vocabSqlId }) => {
    return await ctx.db
      .query("examples")
      .withIndex("by_vocab", (q) => q.eq("vocabSqlId", vocabSqlId))
      .collect();
  },
});

export const searchVocab = query({
  args: { query: v.string(), limit: v.optional(v.number()) },
  handler: async (ctx, { query: q, limit }) => {
    return await ctx.db
      .query("vocabularies")
      .withSearchIndex("search_word", (sq) => sq.search("word", q))
      .take(limit ?? 20);
  },
});

export const getVocabDetail = query({
  args: { sqlId: v.number() },
  handler: async (ctx, { sqlId }) => {
    const vocab = await ctx.db
      .query("vocabularies")
      .withIndex("by_sql_id", (q) => q.eq("sqlId", sqlId))
      .first();
    if (!vocab) return null;

    const subcat = await ctx.db
      .query("subcategories")
      .withIndex("by_sql_id", (q) => q.eq("sqlId", vocab.subcategorySqlId))
      .first();

    const level = subcat
      ? await ctx.db
          .query("levels")
          .withIndex("by_sql_id", (q) => q.eq("sqlId", subcat.levelSqlId))
          .first()
      : null;

    const examples = await ctx.db
      .query("examples")
      .withIndex("by_vocab", (q) => q.eq("vocabSqlId", sqlId))
      .collect();

    return {
      ...vocab,
      subcatTitle: subcat?.title ?? "",
      levelTitle: level?.title ?? "",
      examples,
    };
  },
});


export const getRandomVocabMeanings = query({
  args: { excludeSqlId: v.number(), count: v.number() },
  handler: async (ctx, { excludeSqlId, count }) => {
    // Get a small random batch by sampling recent docs
    const all = await ctx.db
      .query("vocabularies")
      .filter((q) =>
        q.and(
          q.neq(q.field("sqlId"), excludeSqlId),
          q.neq(q.field("meaningVi"), ""),
          q.neq(q.field("meaningVi"), undefined)
        )
      )
      .take(500);
    // Shuffle and take `count`
    const shuffled = all.sort(() => Math.random() - 0.5);
    return shuffled.slice(0, count).map((v) => v.meaningVi ?? "");
  },
});
