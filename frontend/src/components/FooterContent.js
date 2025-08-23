// // import React, { useState, useRef, useEffect, Fragment, useMemo } from 'react';
// // import PropTypes from 'prop-types';
// // import AppBar from '@mui/material/AppBar';
// import Box from '@mui/material/Box';
// // import Toolbar from '@mui/material/Toolbar';
// // import Typography from '@mui/material/Typography';
// // import IconButton from '@mui/material/IconButton';
// // import MenuIcon from '@mui/icons-material/Menu';
// // import AccountCircle from '@mui/icons-material/AccountCircle';
// // import MenuItem from '@mui/material/MenuItem';
// // import Menu from '@mui/material/Menu';
// import Icon from '@mdi/react';
// // import Avatar from '@mui/material/Avatar';
// // import Logout from '@mui/icons-material/Logout';
// // import { ThemeProvider, createTheme } from '@mui/material/styles';
// // import { blue } from '@mui/material/colors';
// // import { Row, Col, Container } from 'react-bootstrap';
// // import Tabs from '@mui/material/Tabs';
// // import Tab from '@mui/material/Tab';
// // import SchoolIcon from '@mui/icons-material/School';
// // import TuneIcon from '@mui/icons-material/Tune';
// // import FilterAltIcon from '@mui/icons-material/FilterAlt';
// // import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
// // import BiotechIcon from '@mui/icons-material/Biotech';
// // import EditOffIcon from '@mui/icons-material/EditOff';
// // import PollIcon from '@mui/icons-material/Poll';
// // import EngineeringIcon from '@mui/icons-material/Engineering';
// // import Avivator from '@/components/avivator/Avivator';
// // import SupportChatSlack from '../../components/slackChat/SupportChatSlack';
// // import SupportChatGCP from '../../components/slackChat/SupportChatGCP';
// // import { Widget, addResponseMessage } from 'react-chat-widget';

// // import UserPage from '../user';
// // import AccountPage from '../account';
// // import { useSelector } from 'react-redux';

// // import store from '../../reducers';
// // import { connect } from 'react-redux';
// // import { getWindowDimensions } from '@/helpers/browser';
// import { mdiChatQuestionOutline } from '@mdi/js';
// // import logo75 from '../../assets/images/logo75.png';
// // import avatarImg from '../../assets/images/avatar.png';

// // import { getVideoSource } from '@/api/experiment';

// const FooterContent = () => {
//   const [showChatFlag, setShowChatFlag] = useState(false);
//   return (
//     <>
//       {/* <SupportChatSlack /> */}
//       <Box
//         style={{
//           bottom: '0px',
//           backgroundColor: '#212529',
//           display: 'flex',
//           position: 'fixed',
//           width: '100%',
//         }}
//       >
//         <button
//           className="btn btn-sm pt-0 pb-0"
//           style={{ marginLeft: 'auto', marginRight: '280px' }}
//           onClick={() => {
//             setShowChatFlag(!showChatFlag);
//           }}
//         >
//           <Icon
//             size={1}
//             horizontal
//             vertical
//             rotate={180}
//             color="#EFEFEF"
//             path={mdiChatQuestionOutline}
//           ></Icon>
//         </button>
//       </Box>
//     </>
//   );
// };

// export default FooterContent;