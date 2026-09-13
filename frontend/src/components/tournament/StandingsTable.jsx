import { Link } from 'react-router-dom';
import EmptyState from '../common/EmptyState';

export default function StandingsTable({ standings }) {
  if (!standings || standings.length === 0) {
    return <EmptyState message="Standings will appear once fixtures are generated." />;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-text-primary text-left">
        <thead>
          <tr className="text-text-secondary text-sm border-b border-text-secondary/30">
            <th className="py-2 pr-4">#</th>
            <th className="py-2 pr-4">Name</th>
            <th className="py-2 pr-4">P</th>
            <th className="py-2 pr-4">W</th>
            <th className="py-2 pr-4">D</th>
            <th className="py-2 pr-4">L</th>
            <th className="py-2 pr-4">Pts</th>
            <th className="py-2 pr-4">+/-</th>
          </tr>
        </thead>
        <tbody>
          {standings.map((s, i) => {
            const linkPath = s.player_id
              ? `/players/${s.player_id}/profile`
              : s.team_id
              ? `/teams/${s.team_id}/roster`
              : null;
            return (
              <tr key={s.participant_id} className="border-b border-text-secondary/10">
                <td className="py-2 pr-4">{i + 1}</td>
                <td className="py-2 pr-4">
                  {linkPath ? (
                    <Link to={linkPath} className="hover:underline">{s.name}</Link>
                  ) : (
                    s.name
                  )}
                </td>
                <td className="py-2 pr-4">{s.played}</td>
                <td className="py-2 pr-4">{s.won}</td>
                <td className="py-2 pr-4">{s.drawn}</td>
                <td className="py-2 pr-4">{s.lost}</td>
                <td className="py-2 pr-4 font-semibold">{s.points}</td>
                <td className="py-2 pr-4">{s.score_difference}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}