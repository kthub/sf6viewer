/**
 * getRecentRankedMatch
 */
export function getRecentRankedMatch(gameRecord) {
  // Get the current date and time in JST
  const jstOffset = 9 * 60 * 60 * 1000; // JST is UTC+9
  const nowJst = new Date(Date.now() + jstOffset);
  const oneWeekAgoJst = new Date(nowJst.getTime() - 7 * 24 * 60 * 60 * 1000);

  // Filter records
  const recentRecords = gameRecord.filter(record => {
    // check date (last 7 days are valid)
    const uploadedDate = new Date(record.UploadedAt * 1000 + jstOffset);
    const isValidDate = (uploadedDate >= oneWeekAgoJst);

    // check match (RANKED MATCH is valid)
    const battleType = record.ReplayReduced.replay_battle_type_name;
    const isValidBattleType = ("RANKED MATCH" === battleType);

    return isValidDate && isValidBattleType;
  });

  return recentRecords.sort((a, b) => a.UploadedAt - b.UploadedAt);
}

/**
 * calculateRank
 */
export function calculateRank(lp) {
  const ranks = [
    { name: 'Master', base: 25000, step: 0 },
    { name: 'Diamond', base: 19000, step: 1200 },
    { name: 'Platinum', base: 13000, step: 1200 },
    { name: 'Gold', base: 9000, step: 800 },
    { name: 'Silver', base: 5000, step: 800 },
    { name: 'Bronze', base: 3000, step: 400 },
    { name: 'Iron', base: 1000, step: 400 },
    { name: 'Rookie', base: 0, step: 200 }
  ];

  for (let i = 0; i < ranks.length; i++) {
    const rank = ranks[i];
    if (lp >= rank.base) {
      const remainingLp = lp - rank.base;
      const divisions = Math.floor(remainingLp / rank.step) + 1;
      const stars = '☆'.repeat(divisions);
      return `${rank.name}${stars ? ' ' + stars : ''}`;
    }
  }
}
