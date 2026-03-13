import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

const KNOWN_THRESHOLD = 5;
const LEARNING_THRESHOLD = 1;

function todayVN(): string {
  // UTC+7
  const d = new Date(Date.now() + 7 * 3600 * 1000);
  return d.toISOString().slice(0, 10);
}

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

    // Track daily activity
    const date = todayVN();
    const daily = await ctx.db
      .query("dailyActivity")
      .withIndex("by_user_date", (q) =>
        q.eq("telegramId", telegramId).eq("date", date)
      )
      .first();

    if (daily) {
      await ctx.db.patch(daily._id, {
        answered: daily.answered + 1,
        correct: daily.correct + (correct ? 1 : 0),
      });
    } else {
      await ctx.db.insert("dailyActivity", {
        telegramId,
        date,
        answered: 1,
        correct: correct ? 1 : 0,
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

export const getDailyReport = query({
  args: { telegramId: v.number() },
  handler: async (ctx, { telegramId }) => {
    const date = todayVN();
    const today = await ctx.db
      .query("dailyActivity")
      .withIndex("by_user_date", (q) =>
        q.eq("telegramId", telegramId).eq("date", date)
      )
      .first();

    // Last 7 days
    const history: { date: string; answered: number; correct: number }[] = [];
    for (let i = 1; i <= 6; i++) {
      const d = new Date(Date.now() + 7 * 3600 * 1000 - i * 86400 * 1000);
      const ds = d.toISOString().slice(0, 10);
      const rec = await ctx.db
        .query("dailyActivity")
        .withIndex("by_user_date", (q) =>
          q.eq("telegramId", telegramId).eq("date", ds)
        )
        .first();
      history.push({ date: ds, answered: rec?.answered ?? 0, correct: rec?.correct ?? 0 });
    }

    return {
      today: { date, answered: today?.answered ?? 0, correct: today?.correct ?? 0 },
      history,
    };
  },
});
