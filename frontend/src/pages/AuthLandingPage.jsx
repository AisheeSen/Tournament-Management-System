import { useNavigate } from 'react-router-dom';
import RoleSelectCard from '../components/auth/RoleSelectCard';
import Button from '../components/common/Button';

export default function AuthLandingPage() {
  const navigate = useNavigate();

  return (
    <div className="app-gradient-bg flex items-center justify-center p-8">
      <div className="w-full max-w-2xl flex flex-col gap-8">
        <Button variant="secondary" onClick={() => navigate(-1)} className="self-start">
          ← Back
        </Button>
        <RoleSelectCard
          title="Player"
          signUpPath="/player/register"
          loginPath="/player/login"
        />
        <RoleSelectCard
          title="Organizer"
          signUpPath="/organizer/register"
          loginPath="/organizer/login"
        />
      </div>
    </div>
  );
}