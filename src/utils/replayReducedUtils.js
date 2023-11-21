/**
 * getRecentRankedMatch
 */
export function getRecentRankedMatch(gameRecord) {
  // Get 1 week ago
  const oneWeekAgoUtc = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
  if (oneWeekAgoUtc.getUTCHours() < 15) {
    oneWeekAgoUtc.setUTCDate(oneWeekAgoUtc.getUTCDate() - 1);
  }
  oneWeekAgoUtc.setUTCHours(15, 0, 0, 0);
  const oneWeekAgoJst = oneWeekAgoUtc;

  // Filter records
  const recentRecords = gameRecord.filter(record => {
    // check date (last 7 days are valid)
    const uploadedDate = new Date(record.UploadedAt * 1000);
    const isValidDate = (uploadedDate >= oneWeekAgoJst);

    // check match (RANKED MATCH is valid)
    const battleType = record.ReplayReduced.replay_battle_type_name;
    const isValidBattleType = ("RANKED MATCH" === battleType);

    // check match (CharacterName is favorite character)
    const favorite_character_name = record.CharacterName;
    const battle_character_name = record.ReplayReduced.character_name;
    const isValidCharacter = (favorite_character_name === battle_character_name);

    return isValidDate && isValidBattleType && isValidCharacter;
  });

  return recentRecords.sort((a, b) => a.UploadedAt - b.UploadedAt);
}

/**
 * addLeagePointAfter
 */
export function addLeaguePointAfter(gameRecord, currentLP) {
  gameRecord.sort((a, b) => a.UploadedAt - b.UploadedAt);
  for (let i = 0; i < gameRecord.length; i++) {
    if (i === gameRecord.length - 1) {
      if (currentLP > 0) {
        gameRecord[i].ReplayReduced.league_point_after = currentLP;
      } else {
        // if currentLP is not provided, set last LP as next best thing.
        gameRecord[i].ReplayReduced.league_point_after = gameRecord[i].ReplayReduced.league_point;
      }
    } else {
      gameRecord[i].ReplayReduced.league_point_after = gameRecord[i + 1].ReplayReduced.league_point;
    }
  }
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
      if (i === 0) {
        return `Master`;
      } else {
        const remainingLp = lp - rank.base;
        const divisions = Math.floor(remainingLp / rank.step) + 1;
        const stars = '☆'.repeat(divisions);
        return `${rank.name}${stars ? ' ' + stars : ''}`;
      }
    }
  }
}
