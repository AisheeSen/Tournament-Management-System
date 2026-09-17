import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import AppShell from '../components/layout/AppShell';
import Card from '../components/common/Card';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorBanner from '../components/common/ErrorBanner';
import EmptyState from '../components/common/EmptyState';
import { getPlayerProfile } from '../api/playerApi';
import { getErrorMessage } from '../utils/errorMessage';

function AchievementRow({ a }) {
  return (
    <Link
      to={`/tournaments/${a.tournament_id}`}
      className="bg-bg-primary rounded-xl px-4 py-3 flex justify-between items-center hover:opacity-90"
    >
      <div>
        <p className="text-text-primary font-semibold">{a.tournament_name}</p>
        <p className="text-text-secondary text-xs">
          {a.sport} · {a.format.replace('_', ' ')}
          {a.team_name && (
            <>
              {' · '}
              <Link
                to={`/teams/${a.team_id}/roster`}
                onClick={(e) => e.stopPropagation()}
                className="underline hover:opacity-80"
              >
                {a.team_name}
              </Link>
            </>
          )}
        </p>
      </div>
      <span className="text-accent">Winner</span>
    </Link>
  );
}

function AchievementSection({ title, items }) {
  return (
    <div className="mb-6">
      <h3 className="text-text-secondary text-sm mb-2">{title}</h3>
      {items.length === 0 ? (
        <p className="text-text-secondary text-sm italic">None yet.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((a) => (
            <AchievementRow key={`${a.tournament_id}-${a.team_id || 'ind'}`} a={a} />
          ))}
        </div>
      )}
    </div>
  );
}

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

  const { individual, current_team, previous_team } = profile.achievements;
  const totalCount = individual.length + current_team.length + previous_team.length;

  return (
    <AppShell>
      <Card className="max-w-2xl">
        <h1 className="text-3xl text-text-primary mb-2">{profile.name}</h1>
        {profile.team_name && (
          <p className="text-text-secondary mb-6">
            Team:{' '}
            <Link to={`/teams/${profile.team_id}/roster`} className="underline hover:opacity-80">
              {profile.team_name}
            </Link>
          </p>
        )}

        <h2 className="text-xl text-text-primary mb-4">🏆 Achievements</h2>

        {totalCount === 0 ? (
          <EmptyState message="No tournament wins yet." />
        ) : (
          <>
            <AchievementSection title="Individual" items={individual} />
            <AchievementSection title="Current Team" items={current_team} />
            <AchievementSection title="Previous Team(s)" items={previous_team} />
          </>
        )}
      </Card>
    </AppShell>
  );
}