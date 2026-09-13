import { useEffect, useState } from 'react';
import AppShell from '../components/layout/AppShell';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import ErrorBanner from '../components/common/ErrorBanner';
import LoadingSpinner from '../components/common/LoadingSpinner';
import { updatePlayerTeam } from '../api/playerApi';
import { listTeams } from '../api/teamApi';
import { getErrorMessage } from '../utils/errorMessage';
import { useAuth } from '../hooks/useAuth';
import { Link } from 'react-router-dom';

export default function PlayerTeamSettingsPage() {
  const { user } = useAuth();
  const [teams, setTeams] = useState([]);
  const [selectedTeamId, setSelectedTeamId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const res = await listTeams();
        setTeams(res.data.items);
        setSelectedTeamId(user?.team_id || '');
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [user]);

  async function handleSave() {
    setError('');
    setSuccess('');
    setSaving(true);
    try {
      await updatePlayerTeam(user.player_id, selectedTeamId ? Number(selectedTeamId) : null);
      setSuccess('Team updated. Refresh to see changes reflected everywhere.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  async function handleLeaveTeam() {
    setError('');
    setSuccess('');
    setSaving(true);
    try {
      await updatePlayerTeam(user.player_id, null);
      setSelectedTeamId('');
      setSuccess('You have left your team.');
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return (
      <AppShell>
        <LoadingSpinner />
      </AppShell>
    );
  }

  return (
    <AppShell>
      <Card className="max-w-md">
        <h1 className="text-2xl text-text-primary mb-2">Team Settings</h1>
        <p className="text-text-secondary text-sm mb-6">
          Current team:{' '}
          {user?.team_name ? (
            <Link to={`/teams/${user.team_id}/roster`} className="underline hover:opacity-80">
              {user.team_name}
            </Link>
          ) : (
            'None'
          )}
        </p>
        <ErrorBanner message={error} />
        {success && <p className="text-text-primary mb-4">{success}</p>}

        <div className="mb-4">
          <label className="block text-text-secondary text-sm mb-2">Join a different team</label>
          <select
            className="w-full bg-transparent border-b border-text-secondary text-text-primary py-2 outline-none focus:border-accent"
            value={selectedTeamId}
            onChange={(e) => setSelectedTeamId(e.target.value)}
          >
            <option value="" className="bg-card">No team</option>
            {teams.map((t) => (
              <option key={t.id} value={t.id} className="bg-card">{t.name}</option>
            ))}
          </select>
        </div>

        <div className="flex gap-3">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? 'Saving...' : 'Save'}
          </Button>
          {user?.team_id && (
            <Button variant="secondary" onClick={handleLeaveTeam} disabled={saving}>
              Leave Current Team
            </Button>
          )}
        </div>
      </Card>
    </AppShell>
  );
}