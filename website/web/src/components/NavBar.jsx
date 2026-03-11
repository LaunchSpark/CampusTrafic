import { NavLink } from 'react-router-dom';
import DateRangePicker from './DateRangePicker';

function NavBar() {
  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
      <div className="container">
        <span className="navbar-brand">WiFi Flow Twin</span>
        <button
          className="navbar-toggler"
          type="button"
          data-bs-toggle="collapse"
          data-bs-target="#mainNavbar"
          aria-controls="mainNavbar"
          aria-expanded="false"
          aria-label="Toggle navigation"
        >
          <span className="navbar-toggler-icon" />
        </button>

        <div className="collapse navbar-collapse" id="mainNavbar">
          <ul className="navbar-nav me-auto mb-2 mb-lg-0">
            <li className="nav-item">
              <NavLink className="nav-link" to="/data">
                Data
              </NavLink>
            </li>
            <li className="nav-item">
              <NavLink className="nav-link" to="/train">
                Train
              </NavLink>
            </li>
          </ul>
          <DateRangePicker />
        </div>
      </div>
    </nav>
  );
}

export default NavBar;
