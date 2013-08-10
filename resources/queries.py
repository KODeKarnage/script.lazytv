# declare file encoding
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html

grab_active_series = """-- QUERY TO GET NEXT EPISODE OF LIVE SHOWS --
SELECT Alpha.Name as ShowName, Alpha.FID as ShowID, LiveEpisode as Episode, LiveSeason as Season, Genre as Genre, Omega.C09 as Length, Omega.C18 as ShowPath, Rating    
FROM episode as Omega
INNER JOIN(
SELECT UnplayedEpisode.idShow as FID, TV.C00 as Name, TV.C08 as Genre, MIN(CAST(UnplayedEpisode.C13 as INT)) as LiveEpisode, LiveSeason, ESLastEpisode, ESLastSeason, TV.C13 as Rating
FROM episode as UnplayedEpisode
INNER JOIN
(
    SELECT MIN(CAST(UnplayedSeason.C12 as INT)) as LiveSeason, ESLastEpisode, ESLastSeason, UnplayedSeason.idShow
    FROM episode as UnplayedSeason
    LEFT JOIN 
        (
        SELECT MAX(CAST(LE.C13 as INT)) as ESLastEpisode, CAST(LE.C12 as INT) as ESLastSeason, LE.idShow, LE.C12
        FROM episode as LE --finds the last watched episode in the last season
        INNER JOIN 
            (
            SELECT MAX(CAST(LW.C12 as INT)) as LastSeason, LW.idShow as LastWatchedShowID, LW.C12
            FROM episode as LW 
            INNER JOIN files as FS 
            ON LW.idFile = FS.idFile 
            WHERE  FS.PlayCount > 0
            GROUP BY LW.idShow
            )
            as LS --finds the last watched season
            ON ESLastSeason = LastSeason
        INNER JOIN files as FE
        ON LE.idFile = FE.idFile 
        WHERE FE.PlayCount > 0 AND ESLastSeason = LastSeason AND LE.idShow = LastWatchedShowID
        GROUP BY LE.idShow
        ) 
        as LP -- returns the season and episode number of the last played episode in the TV SHOW
        ON LP.C12 <= UnplayedSeason.C12
        WHERE LP.idShow = UnplayedSeason.idShow 
        AND (
        (CAST(UnplayedSeason.C12 as INT) = ESLastSeason AND CAST(UnplayedSeason.C13 as INT) > ESLastEpisode) 
        OR 
        (CAST(UnplayedSeason.C12 as INT) > ESLastSeason)
        )
        GROUP BY UnplayedSeason.idShow
) as LS
ON CAST(UnplayedEpisode.C12 as INT) = LiveSeason 
INNER JOIN tvshow as TV ON TV.idShow = UnplayedEpisode.idShow
WHERE UnplayedEpisode.idShow = LS.idShow AND (CAST(UnplayedEpisode.C13 as INT) > ESLastEpisode OR LiveSeason > ESLastSeason)
GROUP BY UnplayedEpisode.idShow
) as Alpha
    ON Alpha.FID = Omega.idShow
    WHERE CAST(Omega.C12 as INT)= LiveSeason AND CAST(Omega.C13 as INT) = LiveEpisode
    GROUP BY Omega.idShow
"""

grab_inactive_series = """-- QUERY TO GET FIRST EPISODE OF UNPLAYED SHOWS --
SELECT t4.C00 as ShowName, e4.idShow as ShowID, episode as Episode, season as Season, t4.C08 as Genre, e4.C09 as Length, e4.C18 as ShowPath, t4.C13 as Rating --FINAL TABLE STRUCTURE
FROM episode as e4
INNER JOIN tvshow as t4
ON t4.idShow = e4.idShow
INNER JOIN
    (SELECT MIN(CAST(e3.C13 as INT)) as episode, season, t3.idShow, t3.C00
    FROM tvshow as t3
    INNER JOIN episode as e3 ON e3.idShow = t3.idShow
    INNER JOIN 
        (SELECT MIN(CAST(e2.C12 as INT)) as season, e2.idShow, t2.C00, PC
        FROM tvshow as t2
        INNER JOIN episode as e2 ON t2.idShow = e2.idShow
        INNER JOIN
            (SELECT e1.idShow, t1.C00, SUM(f1.PlayCount) as PC FROM episode as e1
            INNER JOIN files as f1 ON f1.idFile = e1.idFile
            INNER JOIN tvshow as t1 ON t1.idShow = e1.idShow
            GROUP BY e1.idShow) 
        as PLC ON PLC.idShow = t2.idShow
        WHERE PC is NULL OR PC = 0
        GROUP BY t2.idShow)
    as LP ON LP.idShow = t3.idShow
    WHERE season = CAST(e3.C12 as INT)
    GROUP BY t3.idShow)
as ZX ON ZX.idShow = ShowID
WHERE episode = CAST(e4.C13 as INT) AND season = CAST(e4.c12 as INT)
"""

last_episode_this_season="""    -- query to get the last episode of the current season, if that matches the current episode, then grab the earliest episode of the next season
SELECT MAX(CAST(e1.C13 as INT)) as MaxEpisode FROM episode as e1
WHERE e1.idShow = %i AND CAST(e1.C12 as INT) = %i -- given show ID and season
"""




next_episode_this_season="""     -- query to get the next episode in the current season
SELECT T1.C00 as ShowName, T1.idShow as ShowID, CAST(e2.C13 as INT) as Episode, CAST(e2.C12 as INT) as Season, T1.C08 as Genre, e2.C09 as Length, e2.C18 as ShowPath, T1.C13 as Rating
FROM episode as e2
INNER JOIN tvshow as T1 ON t1.idShow = e2.idShow
INNER JOIN 
    (SELECT MIN(CAST(e1.C13 as INT)) as MINepisode, e1.idShow as ID1
    FROM episode as e1
    WHERE e1.idShow = %i AND CAST(e1.C12 as INT) = %i AND CAST(e1.C13 as INT) > %i)-- give it the show ID and season and last episode
as M1 ON ID1 = e2.idShow
WHERE e2.idShow = %i AND CAST(e2.C12 as INT) = %i AND CAST(e2.C13 as INT) = MINepisode
"""


next_episode_next_season="""    -- query to get the first episode on the next season
SELECT T1.C00 as ShowName, T1.idShow as ShowID, CAST(e3.C13 as INT) as Episode, CAST(e3.C12 as INT) as Season, T1.C08 as Genre, e3.C09 as Length, e3.C18 as ShowPath, T1.C13 as Rating
FROM episode as e3
INNER JOIN tvshow as T1 ON T1.idShow = e3.idShow
INNER JOIN
    (SELECT MIN(CAST(e2.C13 as INT)) as MINepisode, e2.idShow as ID2, MINseason
    FROM episode as e2
    INNER JOIN 
        (SELECT MIN(CAST(e1.C12 as INT)) as MINseason, e1.idShow as ID1 
        FROM episode as e1
        WHERE e1.idShow = %i AND CAST(e1.C12 as INT) > %i) --give it the show and the season
    as S1 ON e2.idShow = ID1
    WHERE e2.idShow = %i)
as S1E1 ON e3.idShow = ID2
WHERE e3.idShow = %i AND CAST(e3.C12 as INT) = MINseason AND CAST(e3.C13 as INT) = MINepisode
"""

latest_partial = """    --- query to get the latest TV show that has been partially watched
SELECT t1.C00 as ShowName, t1.idShow as ShowID, e1.C13 as Episode, e1.C12 as Season, t1.C08 as Genre, e1.C09 as Length, e1.C18 as ShowPath, t1.C13 as Rating, b1.timeInSeconds as Mark, b1.totalTimeInSeconds as Duration
FROM files as f1
INNER JOIN bookmark as b1 ON b1.idFile = f1.idFile
INNER JOIN episode AS e1 ON e1.idFile = f1.idFile
INNER JOIN tvshow as t1 on t1.idShow = e1.idShow
INNER JOIN
    (SELECT b.idFile as ID, MAX(f.lastPlayed) as LP FROM bookmark AS b
        INNER JOIN files as f ON b.idFile = f.idFile
        INNER JOIN episode as e on b.idFile = e.idFile
    WHERE f.playCount IS NULL
    GROUP BY e.idShow
    ) 
as LPP ON LPP.LP = f1.lastPlayed
ORDER BY f1.lastPlayed DESC
"""

all_tv_shows = """    --- query to get the list of TV shows in the library
SELECT t1.C00 as ShowName, t1.idShow as ShowID
FROM tvshow as t1
"""

all_items = """ --- query to get (Name, Genre, Length, rating) for all TV shows
SELECT t.C00 as Name, t.C08 as Genre, e.C09 as Length, t.C13 as Rating
FROM tvshow as t
INNER JOIN episode as e ON e.idShow = t.idShow
GROUP BY t.C00
"""

bookmarks = """ ---query to get the episodes that are in bookmark, i.e. that are partially watched
SELECT e.C18 FROM bookmark as b
INNER JOIN episode as e
ON b.idFile = e.idFile
"""