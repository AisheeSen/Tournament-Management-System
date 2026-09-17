import { useEffect, useState, useMemo } from 'react';
import AppShell from '../components/layout/AppShell';
import TournamentList from '../components/tournament/TournamentList';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorBanner from '../components/common/ErrorBanner';
import { listTournaments } from '../api/tournamentApi';
import { getErrorMessage } from '../utils/errorMessage';
import { useAuth } from '../hooks/useAuth';

export default function HomePage() {
  const { user } = useAuth();
  const [upcoming, setUpcoming] = useState([]);
  const [live, setLive] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError('');
      try {
        const [regOpen, ongoing, done] = await Promise.all([
          listTournaments({ status: 'REGISTRATION_OPEN', perPage: 10 }),
          listTournaments({ status: 'ONGOING', perPage: 10 }),
          listTournaments({ status: 'COMPLETED', perPage: 5 }),
        ]);
        setUpcoming(regOpen.data.items);
        setLive(ongoing.data.items);
        setCompleted(done.data.items);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filterList = (list) => {
    if (!search.trim()) return list;
    const q = search.toLowerCase();
    return list.filter(
      (t) => t.name.toLowerCase().includes(q) || t.sport.toLowerCase().includes(q)
    );
  };

  const filteredUpcoming = useMemo(() => filterList(upcoming), [upcoming, search]);
  const filteredLive = useMemo(() => filterList(live), [live, search]);
  const filteredCompleted = useMemo(() => filterList(completed), [completed, search]);

  return (
    <AppShell>
      <div className="flex justify-end mb-6">
        <input
          type="text"
          placeholder="Search by name or sport..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-sidebar text-text-primary placeholder-text-secondary rounded-full px-5 py-2 w-[32rem] max-w-full outline-none focus:ring-2 focus:ring-accent"
        />
      </div>

      <div className="bg-gradient-to-r from-bg-secondary to-accent rounded-3xl p-8 mb-8">
        <h1 className="text-3xl text-text-primary">
          Hello{user ? `, ${user.name}` : ''}
        </h1>
        <p className="text-text-secondary mt-2">
          Browse tournaments, view live matches, and check results.
        </p>
      </div>

      <ErrorBanner message={error} />
      {loading ? (
        <LoadingSpinner />
      ) : (
        <>
          {filteredLive.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl text-text-primary mb-4">🔴 Live</h2>
              <TournamentList tournaments={filteredLive} />
            </section>
          )}

          <section className="mb-8">
            <h2 className="text-2xl text-text-primary mb-4">Upcoming Tournaments</h2>
            <TournamentList tournaments={filteredUpcoming} />
          </section>

          {filteredCompleted.length > 0 && (
            <section className="mb-8">
              <h2 className="text-2xl text-text-primary mb-4">Previous Results</h2>
              <TournamentList tournaments={filteredCompleted} />
            </section>
          )}
        </>
      )}
    </AppShell>
  );
}