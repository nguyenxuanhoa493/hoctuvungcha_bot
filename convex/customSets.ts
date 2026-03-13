import { mutation, query } from "./_generated/server";
import { v } from "convex/values";
import { Id } from "./_generated/dataModel";

export const listSets = query({
  args: { telegramId: v.number() },
  handler: async (ctx, { telegramId }) => {
    return await ctx.db
      .query("userCustomSets")
      .withIndex("by_user", (q) => q.eq("telegramId", telegramId))
      .collect();
  },
});

export const getSet = query({
  args: { setId: v.string() },
  handler: async (ctx, { setId }) => {
    return await ctx.db.get(setId as Id<"userCustomSets">);
  },
});

export const createSet = mutation({
  args: { telegramId: v.number(), name: v.string() },
  handler: async (ctx, { telegramId, name }) => {
    return await ctx.db.insert("userCustomSets", {
      telegramId,
      name,
      vocabIds: [],
    });
  },
});

export const addWord = mutation({
  args: { setId: v.string(), vocabId: v.number() },
  handler: async (ctx, { setId, vocabId }) => {
    const set = await ctx.db.get(setId as Id<"userCustomSets">);
    if (!set) return;
    if (!set.vocabIds.includes(vocabId)) {
      await ctx.db.patch(set._id, { vocabIds: [...set.vocabIds, vocabId] });
    }
  },
});

export const removeWord = mutation({
  args: { setId: v.string(), vocabId: v.number() },
  handler: async (ctx, { setId, vocabId }) => {
    const set = await ctx.db.get(setId as Id<"userCustomSets">);
    if (!set) return;
    await ctx.db.patch(set._id, {
      vocabIds: set.vocabIds.filter((id) => id !== vocabId),
    });
  },
});

export const deleteSet = mutation({
  args: { setId: v.string() },
  handler: async (ctx, { setId }) => {
    await ctx.db.delete(setId as Id<"userCustomSets">);
  },
});
