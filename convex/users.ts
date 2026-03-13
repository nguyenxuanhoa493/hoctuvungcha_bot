import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const upsertUser = mutation({
  args: {
    telegramId: v.number(),
    username: v.optional(v.string()),
    firstName: v.string(),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("botUsers")
      .withIndex("by_telegram_id", (q) => q.eq("telegramId", args.telegramId))
      .first();
    if (existing) {
      await ctx.db.patch(existing._id, {
        username: args.username,
        firstName: args.firstName,
      });
    } else {
      await ctx.db.insert("botUsers", args);
    }
  },
});

export const setDailyGoal = mutation({
  args: { telegramId: v.number(), goal: v.number() },
  handler: async (ctx, { telegramId, goal }) => {
    const user = await ctx.db
      .query("botUsers")
      .withIndex("by_telegram_id", (q) => q.eq("telegramId", telegramId))
      .first();
    if (user) await ctx.db.patch(user._id, { dailyGoal: goal });
  },
});

export const getUser = query({
  args: { telegramId: v.number() },
  handler: async (ctx, { telegramId }) => {
    return await ctx.db
      .query("botUsers")
      .withIndex("by_telegram_id", (q) => q.eq("telegramId", telegramId))
      .first();
  },
});
