import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import Card from '../components/common/Card';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorBanner from '../components/common/ErrorBanner';
import EmptyState from '../components/common/EmptyState';
import { getTeam, getTeamAchievements } from '../api/teamApi';
import { listPlayers } from '../api/playerApi';
import { getErrorMessage } from '../utils/errorMessage';

export default function TeamRosterPage() {
  const { id } = useParams();
  const [team, setTeam] = useState(null);
  const [members, setMembers] = useState([]);
  const [achievements, setAchievements] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const [teamRes, playersRes, achievementsRes] = await Promise.all([
          getTeam(id),
          listPlayers(1, 200),
          getTeamAchievements(id),
        ]);
        setTeam(teamRes.data);
        setMembers(playersRes.data.items.filter((p) => p.team_id === Number(id)));
        setAchievements(achievementsRes.data.achievements);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [id]);

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner />
      </AppShell>
    );
  }

  if (error || !team) {
    return (
      <AppShell>
        <ErrorBanner message={error || 'Team not found.'} />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <h1 className="text-3xl text-text-primary mb-6">{team.name}</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <h2 className="text-xl text-text-primary mb-4">Roster ({members.length})</h2>
          {members.length === 0 ? (
            <EmptyState message="No players on this team yet." />
          ) : (
            <div className="flex flex-col gap-2">
              {members.map((m) => (
                <Link
                  key={m.id}
                  to={`/players/${m.id}/profile`}
                  className="bg-bg-primary rounded-xl px-4 py-2 text-text-primary hover:opacity-90 block"
                >
                  {m.name}
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h2 className="text-xl text-text-primary mb-4">🏆 Achievements ({achievements.length})</h2>
          {achievements.length === 0 ? (
            <EmptyState message="No tournament wins yet." />
          ) : (
            <div className="flex flex-col gap-2">
              {achievements.map((a) => (
                <Link
                  key={a.tournament_id}
                  to={`/tournaments/${a.tournament_id}`}
                  className="bg-bg-primary rounded-xl px-4 py-3 flex justify-between items-center hover:opacity-90"
                >
                  <div>
                    <p className="text-text-primary font-semibold">{a.tournament_name}</p>
                    <p className="text-text-secondary text-xs">
                      {a.sport} · {a.format.replace('_', ' ')}
                    </p>
                  </div>
                  <span className="text-accent">Winner</span>
                </Link>
              ))}
            </div>
          )}
        </Card>
      </div>
    </AppShell>
  );
}