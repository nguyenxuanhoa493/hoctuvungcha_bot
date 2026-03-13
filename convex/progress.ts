import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const KNOWN_THRESHOLD = 5;   // correct streak to mark as "known"
const LEARNING_THRESHOLD = 1; // at least 1 correct to move from "new" to "learning"

export const getWordProgress = query({
  args: { telegramId: v.number(), vocabId: v.number() },
  handler: async (ctx, { telegramId, vocabId }) => {
    return await ctx.db
      .query("userWordProgress")
      .withIndex("by_user_vocab", (q) =>
        q.eq("telegramId", telegramId).eq("vocabId", vocabId)
      )
      .first();
  },
});

export const upsertWordProgress = mutation({
  args: {
    telegramId: v.number(),
    vocabId: v.number(),
    correct: v.boolean(),
  },
  handler: async (ctx, { telegramId, vocabId, correct }) => {
    const existing = await ctx.db
      .query("userWordProgress")
      .withIndex("by_user_vocab", (q) =>
        q.eq("telegramId", telegramId).eq("vocabId", vocabId)
      )
      .first();

    const now = Date.now();

    if (existing) {
      const correctCount = correct ? existing.correctCount + 1 : existing.correctCount;
      const wrongCount = correct ? existing.wrongCount : existing.wrongCount + 1;
      let status = existing.status;
      if (correctCount >= KNOWN_THRESHOLD) status = "known";
      else if (correctCount >= LEARNING_THRESHOLD) status = "learning";
      if (!correct && status === "known") status = "learning";

      await ctx.db.patch(existing._id, {
        correctCount,
        wrongCount,
        status,
        lastReviewedAt: now,
      });
    } else {
      await ctx.db.insert("userWordProgress", {
        telegramId,
        vocabId,
        correctCount: correct ? 1 : 0,
        wrongCount: correct ? 0 : 1,
        status: correct ? "learning" : "new",
        lastReviewedAt: now,
      });
    }
  },
});

export const getStats = query({
  args: { telegramId: v.number() },
  handler: async (ctx, { telegramId }) => {
    const all = await ctx.db
      .query("userWordProgress")
      .withIndex("by_user", (q) => q.eq("telegramId", telegramId))
      .collect();

    const counts = { new: 0, learning: 0, known: 0 };
    for (const p of all) {
      if (p.status === "known") counts.known++;
      else if (p.status === "learning") counts.learning++;
      else counts.new++;
    }
    return { ...counts, total: all.length };
  },
});
