import { useSelector, connect } from "react-redux";
import store from '../reducers';
import { mdiChatQuestionOutline } from '@mdi/js';
import logo75 from '../assets/images/logo75.png';
import IconButton from '@mui/material/IconButton';
import ManageAccountsIcon from '@mui/icons-material/ManageAccounts';
import ArrowBackSharpIcon from '@mui/icons-material/ArrowBackSharp';
import AccountCircle from '@mui/icons-material/AccountCircle';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Menu from '@mui/material/Menu';
import Icon from '@mdi/react';
import Avatar from '@mui/material/Avatar';
import Logout from '@mui/icons-material/Logout';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { blue } from '@mui/material/colors';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Toolbar from '@mui/material/Toolbar';
import { useState } from "react";
import { useFlagsStore } from "@/state";
import { UserLogout } from "@/utils";


const mapStateToProps = (state) => ({});

const HeaderContent = ({nav=null}) => {  
  const DialogShowChatFlag = useFlagsStore((store) => store.DialogShowChatFlag);
  const MenuAnchorElement = useFlagsStore((store) => store.MenuAnchorElement);
  const AdminMenuAnchorElement = useFlagsStore((store) => store.AdminMenuAnchorElement);

  const user = useSelector((state) => state.auth.user);
  let initialName = '';
  if (user === null) {
    initialName = '';
  } else if (user.fullName.length > 0) {
    const nameArray = user.fullName.split(' ');
    nameArray.forEach((name) => {
      if (name.length <= 0) return;
      initialName += name.charAt(0).toUpperCase();
    });
  }

  const darkTheme = createTheme({
    palette: {
      mode: 'dark',
      primary: {
        main: '#1976d2',
      },
    },
  });

  const handleMenu = (event) => {
    useFlagsStore.setState({ MenuAnchorElement: event.currentTarget });
  };
  const handleClose = () => {
    useFlagsStore.setState({ MenuAnchorElement: null });
  };
  const handleAdminMenu = (event) => {
    useFlagsStore.setState({ AdminMenuAnchorElement: event.currentTarget });
  };
  const handleAdminClose = () => {
    useFlagsStore.setState({ AdminMenuAnchorElement: null });
  };

  const handleLogout = () => {
    UserLogout();
  };

  const handleUserPage = () => {
    useFlagsStore.setState({ AccountPageFlag: false });
    useFlagsStore.setState({ AccountHistoryPageFlag: false });
    useFlagsStore.setState({ VivPageFlag: false });
    useFlagsStore.setState({ UserPageFlag: true });
    useFlagsStore.setState({ AdminUserAccountManagementFlag: false });
  };
  const handleOpenAccount = () => {
    useFlagsStore.setState({ AccountPageFlag: true });
    useFlagsStore.setState({ AccountHistoryPageFlag: false });
    useFlagsStore.setState({ VivPageFlag: false });
    useFlagsStore.setState({ UserPageFlag: false });
    useFlagsStore.setState({ AdminUserAccountManagementFlag: false });
  };
  const handleOpenAccountHistory = () => {
    useFlagsStore.setState({ AccountPageFlag: false });
    useFlagsStore.setState({ AccountHistoryPageFlag: true });
    useFlagsStore.setState({ VivPageFlag: false });
    useFlagsStore.setState({ UserPageFlag: false });
    useFlagsStore.setState({ AdminUserAccountManagementFlag: false });
  };
  const handleOpenViv = () => {
    useFlagsStore.setState({ AccountPageFlag: false });
    useFlagsStore.setState({ AccountHistoryPageFlag: false });
    useFlagsStore.setState({ VivPageFlag: true });
    useFlagsStore.setState({ UserPageFlag: false });
    useFlagsStore.setState({ AdminUserAccountManagementFlag: false });
  };
  const handleOpenAdminUserAccountManagement = () => {
    useFlagsStore.setState({ AccountPageFlag: false });
    useFlagsStore.setState({ AccountHistoryPageFlag: false });
    useFlagsStore.setState({ VivPageFlag: false });
    useFlagsStore.setState({ UserPageFlag: false });
    useFlagsStore.setState({ AdminUserAccountManagementFlag: true });
  };

  const goHome = () => {
    store.dispatch({
      type: 'auth_changeWorkbench',
      payload: null,
    });

    window.history.pushState({}, '', '/ias');
  }

  return (
    <Box sx={{ flexGrow: 1, height: '65px' }} id='main-panel-header'>
      <ThemeProvider theme={darkTheme}>
        <AppBar className="main-header" position="static">
          <Toolbar>
            <IconButton
              size="large"
              aria-label="account of current user"
              aria-controls="menu-appbar"
              aria-haspopup="true"
              color="inherit"
              onClick={goHome}
            >
              <ArrowBackSharpIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              <img width="116" height="48" src={logo75} alt="Logo" />
            </Typography>
            <div>
              {/* {user.isAdmin && <IconButton
                color="primary"
                aria-label="Administration & Management"
                onClick={handleAdminMenu}
                color="inherit"
                aria-controls="menu-admin-management"
                aria-haspopup="true"
              >
                <ManageAccountsIcon />
              </IconButton>}
              <Menu
                id="menu-admin-management"
                anchorEl={AdminMenuAnchorElement}
                anchorOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
                keepMounted
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
                open={Boolean(AdminMenuAnchorElement)}
                onClose={handleAdminClose}
              >
                <MenuItem onClick={handleOpenAdminUserAccountManagement}>Manage User Accounts</MenuItem>
              </Menu> */}

              <IconButton
                size="large"
                aria-label="account of current user"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                color="inherit"
                className="btn btn-sm"
                style={{}}
                onClick={() => {
                  store.dispatch({
                    type: 'UPDATE_PATH_GPT_CHAT_DIALOG_STATUS',
                    payload: true,
                  });
                }}
              >
                <Icon
                  size={1}
                  horizontal
                  vertical
                  rotate={180}
                  color="#EF0000"
                  path={mdiChatQuestionOutline}
                ></Icon>
              </IconButton>
              <IconButton
                size="large"
                aria-label="account of current user"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                color="inherit"
                className="btn btn-sm"
                style={{}}
                onClick={() => {
                  useFlagsStore.setState({ DialogShowChatFlag: !DialogShowChatFlag });
                }}
              >
                <Icon
                  size={1}
                  horizontal
                  vertical
                  rotate={180}
                  color="#EFEFEF"
                  path={mdiChatQuestionOutline}
                ></Icon>
              </IconButton>
              <IconButton
                size="large"
                aria-label="account of current user"
                aria-controls="menu-appbar"
                aria-haspopup="true"
                onClick={handleMenu}
                color="inherit"
              >
                <AccountCircle />
              </IconButton>
              <Menu
                id="menu-appbar"
                anchorEl={MenuAnchorElement}
                anchorOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
                keepMounted
                transformOrigin={{
                  vertical: 'top',
                  horizontal: 'right',
                }}
                open={Boolean(MenuAnchorElement)}
                onClose={handleClose}
              >
                <MenuItem onClick={handleOpenViv}>My Workspace</MenuItem>
                <MenuItem onClick={handleOpenAccount}>My account</MenuItem>
                <MenuItem onClick={handleOpenAccountHistory}>Account History</MenuItem>
              </Menu>
              <IconButton size="large" onClick={handleUserPage}>
                <Avatar sx={{ width: 30, height: 30, bgcolor: blue[500] }}>
                  {' '}
                  {initialName}{' '}
                </Avatar>
              </IconButton>
              <IconButton size="large" onClick={handleLogout} color="inherit">
                <Logout />
              </IconButton>
            </div>
          </Toolbar>
        </AppBar>
      </ThemeProvider>
    </Box>
  );
};

export default connect(mapStateToProps)(HeaderContent); // connect wrapper function in use