import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import Card from '../components/common/Card';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorBanner from '../components/common/ErrorBanner';
import EmptyState from '../components/common/EmptyState';
import { getPlayerProfile } from '../api/playerApi';
import { getErrorMessage } from '../utils/errorMessage';

export default function PlayerProfilePage() {
  const { id } = useParams();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const res = await getPlayerProfile(id);
        setProfile(res.data);
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

  if (error || !profile) {
    return (
      <AppShell>
        <ErrorBanner message={error || 'Player not found.'} />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Card className="max-w-2xl">
        <h1 className="text-3xl text-text-primary mb-2">{profile.name}</h1>
        {profile.team_name && (
          <p className="text-text-secondary mb-6">
            Team:{' '}
            <Link to={`/teams/${profile.team_id}/roster`} className="text-accent underline">
              {profile.team_name}
            </Link>
          </p>
        )}

        <h2 className="text-xl text-text-primary mb-4">🏆 Achievements</h2>
        {profile.achievements.length === 0 ? (
          <EmptyState message="No tournament wins yet." />
        ) : (
          <div className="flex flex-col gap-2">
            {profile.achievements.map((a) => (
              <Link
                key={a.tournament_id}
                to={`/tournaments/${a.tournament_id}`}
                className="bg-bg-primary rounded-xl px-4 py-3 flex justify-between items-center hover:opacity-90"
              >
                <div>
                  <p className="text-text-primary font-semibold">{a.tournament_name}</p>
 		  <p className="text-text-secondary text-xs">
   		     {a.sport} · {a.format.replace('_', ' ')} · {a.participant_type}
    		     {a.team_name && ` · ${a.team_name}`}
  		  </p>
                </div>
                <span className="text-accent">Winner</span>
              </Link>
            ))}
          </div>
        )}
      </Card>
    </AppShell>
  );
}