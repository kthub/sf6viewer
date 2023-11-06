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

  return recentRecords;
}
